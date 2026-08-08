import razorpay

from django.conf import settings
from django.db import transaction

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView
from rest_framework import status

from apps.carts.models import Cart, CartItem
from .models import Payment, PaymentStatusHistory
from .services import PaymentService, client

OUTCOME_STATUS_MAP = {
    "success": status.HTTP_200_OK,
    "failed": status.HTTP_200_OK,
    "already_handled": status.HTTP_200_OK,
    "unfulfilled": status.HTTP_200_OK,
    "ignored": status.HTTP_200_OK,
    "not_found": status.HTTP_400_BAD_REQUEST,
}


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
    """
    HTTP-only: verifies the signature, extracts the payload, delegates
    all business logic to PaymentService, and translates the outcome
    into an HTTP response. No business logic belongs in this class.
    """

    permission_classes = [AllowAny]

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
        
        result = PaymentService(request.data).process()

        http_status = OUTCOME_STATUS_MAP.get(result["outcome"], status.HTTP_200_OK)
        
        return Response({"message": result["message"]}, status=http_status)