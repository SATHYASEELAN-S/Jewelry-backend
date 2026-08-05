import logging

import razorpay

from django.conf import settings
from django.db import transaction

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView
from rest_framework import status

from apps.accounts.models import Address
from apps.carts.models import Cart, CartItem
from apps.orders.models import Order, OrderItem
from apps.products.models import ProductVariant
from .models import Payment, PaymentStatusHistory

logger = logging.getLogger(__name__)

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


class InitiatePaymentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)

        if not cart_items:
            raise ValidationError("Cart items is empty.")

        items_stock = []
        cart_snapshot = []
        for item in cart_items:
            stock = item.variant.stock
            if item.quantity > stock:
                items_stock.append({f"{item.variant}": f"only {stock} items left."})
            cart_snapshot.append(
                {
                    "variant_id": str(item.variant.public_id),
                    "product_name": item.variant.product.name,
                    "size": item.variant.size,
                    "quantity": item.quantity,
                    "unit_price": str(item.unit_price),
                    "subtotal": str(item.subtotal),
                }
            )

        if items_stock:
            raise ValidationError(items_stock)

        total_amount = cart.total_price

        razorpayment_order = client.order.create(
            {
                "amount": int(total_amount * 100),
                "currency": "INR",
                "payment_capture": 1,
            }
        )

        payment = Payment.objects.create(
            user=request.user,
            cart=cart,
            cart_snapshot=cart_snapshot,
            amount=total_amount,
            razorpay_order_id=razorpayment_order["id"],
        )

        PaymentStatusHistory.objects.create(payment=payment, status="created")

        return Response(
            {
                "key_id": settings.RAZORPAY_KEY_ID,
                "razorpay_order_id": razorpayment_order["id"],
                "amount": razorpayment_order["amount"],
                "currency": razorpayment_order["currency"],
            }
        )


class RazorpayWebhookAPIView(APIView):
    permission_classes = [AllowAny]

    def get_payment(self, razorpay_order_id):
        """Returns the Payment or None. Caller is responsible for the 400 response."""
        return Payment.objects.filter(razorpay_order_id=razorpay_order_id).first()

    def issue_refund(self, payment, razorpay_payment_id):
        """
        Attempts a refund for a paid-but-unfulfilled payment.
        Returns a Response — caller just returns it directly.
        """
        try:
            refund = client.payment.refund(
                razorpay_payment_id,
                {"amount": int(payment.amount * 100), "speed": "normal"},
            )
        except razorpay.errors.BadRequestError as e:
            msg = str(e)
            if "already been refunded" in msg or "fully refunded" in msg:
                # Razorpay's state and ours disagree — trust Razorpay and reconcile.
                payment.set_status("refunded")
                logger.info(
                    "Payment %s already refunded on Razorpay, reconciled local state.",
                    payment.razorpay_order_id,
                )
                return Response(
                    {"message": "Already refunded on Razorpay, state reconciled"},
                    status=status.HTTP_200_OK,
                )

            payment.set_status("refund_failed")
            logger.error(
                "Refund failed for payment %s: %s", payment.razorpay_order_id, msg
            )
            return Response(
                {"message": f"Refund failed: {msg}"}, status=status.HTTP_200_OK
            )

        payment.razorpay_refund_id = refund["id"]
        payment.save(update_fields=["razorpay_refund_id"])
        payment.set_status("refund_processing")

        return Response(
            {"message": "Order could not be fulfilled, refund initiated"},
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def post(self, request):
        signature = request.headers.get("X-Razorpay-Signature")

        try:
            client.utility.verify_webhook_signature(
                request.body.decode(), signature, settings.RAZORPAY_WEBHOOK_SECRET
            )
        except razorpay.errors.SignatureVerificationError:
            return Response(
                {"message": "Invalid Signature"}, status=status.HTTP_400_BAD_REQUEST
            )

        payload = request.data
        event = payload.get("event")
        payment_entity = payload["payload"]["payment"]["entity"]
        razorpay_order_id = payment_entity["order_id"]
        razorpay_payment_id = payment_entity["id"]

        payment = self.get_payment(razorpay_order_id)
        if payment is None:
            return Response(
                {"message": "Payment not found"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Lock the row for the duration of this transaction so concurrent/retried
        # webhook deliveries for the same payment can't race each other.
        payment = Payment.objects.select_for_update().get(pk=payment.pk)

        logger.info("Razorpay webhook event=%s order=%s", event, razorpay_order_id)

        if event == "payment.failed":
            payment.razorpay_payment_id = razorpay_payment_id
            payment.save(update_fields=["razorpay_payment_id"])
            payment.set_status("failed")
            return Response(
                {"message": "Payment marked as failed"}, status=status.HTTP_200_OK
            )

        if event == "refund.processed":
            payment.set_status("refunded")
            return Response({"message": "Refund processed"}, status=status.HTTP_200_OK)
        
        if event == "refund.created":
            payment.set_status("refund_processing")
            return Response({"message": "Refund is processing"}, status=status.HTTP_200_OK)

        if event == "refund.failed":
            payment.set_status("refund_failed")
            return Response({"message": "Refund failed"}, status=status.HTTP_200_OK)

        if event != "payment.captured":
            return Response({"message": "Event ignored"}, status=status.HTTP_200_OK)

        current_status = payment.status

        if current_status == "success":
            return Response({"message": "Already processed"}, status=status.HTTP_200_OK)

        if current_status == "paid_unfulfilled":
            return Response(
                {"message": "Already handled as unfulfilled"}, status=status.HTTP_200_OK
            )

        if current_status == "refund_processing":
            return Response(
                {"message": "Refund already in progress"}, status=status.HTTP_200_OK
            )

        cart = payment.cart
        cart_items = CartItem.objects.filter(cart=cart)

        items_stock = []
        locked_variants = {}
        unfulfilled = False

        for item in cart_items:
            try:
                variant = ProductVariant.objects.select_for_update().get(
                    public_id=item.variant_id
                )
            except ProductVariant.DoesNotExist:
                unfulfilled = True
                break

            locked_variants[item.id] = variant
            if variant.stock < item.quantity:
                items_stock.append(f"{variant}: only {variant.stock} left")

        if unfulfilled or items_stock:
            payment.razorpay_payment_id = razorpay_payment_id
            payment.save(update_fields=["razorpay_payment_id"])
            payment.set_status("paid_unfulfilled")

            return self.issue_refund(payment, razorpay_payment_id)

        address = Address.objects.filter(user=payment.user, is_default=True).first()

        order = Order.objects.create(
            user=payment.user,
            shipping_street=address.street,
            shipping_city=address.city,
            shipping_state=address.state,
            shipping_pincode=address.pincode,
            shipping_landmark=address.landmark,
            total_price=cart.total_price,
           
        )

        order.set_status("pending")

        for item in cart_items:
            variant = locked_variants[item.id]
            variant.stock -= item.quantity
            variant.save(update_fields=["stock"])

            OrderItem.objects.create(
                order=order,
                variant=variant,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )

            item.delete()

        payment.order = order
        payment.razorpay_payment_id = razorpay_payment_id
        payment.save(update_fields=["order", "razorpay_payment_id"])
        payment.set_status("success")

        order.set_status("confirmed")
        
        return Response({"message": "Payment processed, order created"}, status=200)