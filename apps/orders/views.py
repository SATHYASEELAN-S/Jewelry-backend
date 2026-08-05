from django.db import transaction

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import (
    RetrieveAPIView,
    ListAPIView,
    UpdateAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ValidationError

from apps.carts.models import Cart, CartItem
from apps.accounts.models import Address
from apps.products.models import ProductVariant
from .models import Order, OrderItem, OrderStatusHistory
from .serializers import (
    OrderSerializer,
    OrderCancelSerializer,
    OrderItemSerializer,
    OrderStatusHistorySerializer,
)


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

        order = Order.objects.create(
            user=request.user,
            shipping_street=address.street,
            shipping_city=address.city,
            shipping_state=address.state,
            shipping_pincode=address.pincode,
            shipping_landmark=address.landmark,
            total_price=cart.total_price,
        )

        order.set_status("pending")

        for item in cart_items:
            variant = item.variant
            variant.stock -= item.quantity
            variant.save(update_fields=["stock"])
            OrderItem.objects.create(
                order=order,
                variant=item.variant,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
            item.delete()

        order.set_status("confirmed")

        serializer = OrderSerializer(order)
        return Response(serializer.data)


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
                f"You can't cancel this order. This item has been already {order.status}"
            )

        order.set_status("cancelled")

        return Response(OrderSerializer(order).data)


class OrderAPIView(ListAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
