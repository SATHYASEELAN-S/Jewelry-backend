import razorpay
from apps.accounts.models import Address
from apps.carts.models import Cart, CartItem
from apps.orders.models import Order, OrderItem, OrderStatusHistory
from apps.products.models import ProductVariant
from django.conf import settings
from django.db import transaction
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView
from rest_framework import status

from .models import Payment

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
                "payment_capture": 0,
            }
        )

        payment = Payment.objects.create(
            user=request.user,
            cart=cart,
            cart_snapshot=cart_snapshot,
            amount=total_amount,
            status="created",
            razorpay_order_id=razorpayment_order["id"],
        )

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

    def get_payment(self,razorpay_order_id):
        try:
            return Payment.objects.get(razorpay_order_id=razorpay_order_id)
        except Payment.DoesNotExist:
            return Response(
                {"message": "Payment not found"}, status=status.HTTP_400_BAD_REQUEST
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

        if event == "payment.failed":
            payment_entity = payload["payload"]["payment"]["entity"]
            razorpay_order_id = payment_entity["order_id"]
            razorpay_payment_id = payment_entity["id"]
            payment = self.get_payment(razorpay_order_id)

            payment.status = "failed"
            payment.razorpay_payment_id = razorpay_payment_id
            payment.save(update_fields=["status", "razorpay_payment_id"])

            return Response(
                {"message": "Payment marked as failed"}, status=status.HTTP_200_OK
            )

        if not event in ("payment.captured", "payment.authorized"):
            return Response({"message": "Event ignored"}, status=status.HTTP_200_OK)
        payment_entity = payload["payload"]["payment"]["entity"]
        razorpay_order_id = payment_entity["order_id"]
        razorpay_payment_id = payment_entity["id"]
        payment = self.get_payment(razorpay_order_id)

        if payment.status == "success":
            return Response({"message": "Already processed"}, status=status.HTTP_200_OK)

        if payment.status == "paid_unfulfilled":
            return Response(
                {"message": "Already handled as unfulfilled"}, status=status.HTTP_200_OK
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
            payment.status = "paid_unfulfilled"
            payment.razorpay_payment_id = razorpay_payment_id
            payment.save(update_fields=["status", "razorpay_payment_id"])
            return Response(
                {"message": "Order could not be fulfilled, marked for refund"},
                status=status.HTTP_200_OK,
            )

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

        OrderStatusHistory.objects.create(order=order, status="pending")

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
        payment.status = "success"
        payment.order = order 
        payment.razorpay_payment_id = razorpay_payment_id
        payment.save(update_fields=["status", "order", "razorpay_payment_id"])
        return Response({"message": "Payment processed, order created"}, status=200)
