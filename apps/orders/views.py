from django.db import transaction

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ValidationError

from apps.carts.models import Cart, CartItem
from apps.accounts.models import Address
from apps.products.models import ProductVariant
from .models import Order, OrderItem, OrderStatusHistory
from .serializers import (
    OrderSerializer,
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

        OrderStatusHistory.objects.create(order=order, status="pending")
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

        OrderStatusHistory.objects.create(order=order, status="confirmed")

        serializer = OrderSerializer(order)
        return Response(serializer.data)

class OrderDetailAPIView(RetrieveAPIView):
    serializer_class = OrderSerializer
    lookup_field = 'public_id'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
    
class OrderAPIView(ListAPIView):
    serializer_class = OrderSerializer
    

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
