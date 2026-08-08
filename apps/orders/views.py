from django.db import transaction

from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView

from apps.accounts.models import Address
from apps.carts.models import Cart, CartItem
from apps.payments.models import Payment
from apps.payments.services import RefundService
from apps.products.models import ProductVariant

from .models import Order, OrderItem
from .serializers import OrderCancelSerializer, OrderSerializer


class CheckoutAPIView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    @transaction.atomic
    def post(self, request):
        address = Address.objects.filter(user=request.user, is_default=True).first()

        if not address:
            raise ValidationError("Address is required.")

        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)

        if not cart_items:
            raise ValidationError("Cart items is empty.")

        items_stock = []
        for item in cart_items:
            stock = item.variant.stock
            if item.quantity > stock:
                items_stock.append({f"{item.variant}": f"only {stock} items left."})

        if items_stock:
            raise ValidationError(items_stock)

        return Response({"message": "Ready to payment"}, status=status.HTTP_200_OK)


class OrderDetailAPIView(RetrieveUpdateAPIView):
    lookup_field = "public_id"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return OrderCancelSerializer
        return OrderSerializer

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        order = (
            self.get_queryset()
            .select_for_update()
            .get(public_id=kwargs[self.lookup_field])
        )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cancel = serializer.validated_data["cancel"]

        if not cancel:
            raise ValidationError("cancel must be true to cancel this order.")

        if order.status != "confirmed":
            raise ValidationError(
                f"You can't cancel this order because its current status is {order.status}."
            )

        payment = Payment.objects.filter(order=order).first()
        if payment is None:
            raise ValidationError("No payment record found for this order.")

        order_items = OrderItem.objects.select_related("variant").filter(order=order)
        for item in order_items:
            variant = ProductVariant.objects.select_for_update().get(pk=item.variant_id)
            variant.stock += item.quantity
            variant.save(update_fields=["stock"])

        result = RefundService().issue_refund(payment, payment.razorpay_payment_id)

        order.set_status("cancelled")
        return Response({"message": result["message"]}, status=status.HTTP_200_OK)


class OrderAPIView(ListAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
