from django.db import transaction

from rest_framework import status
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .models import Cart, CartItem
from .serializers import CartItemSerializer, CartItemDetailSerializer
from apps.products.models import ProductVariant


class CartItemAPIView(ListCreateAPIView):
    serializer_class = CartItemSerializer
    pagination_class = None

    def get_or_create_cart(self):
        """
        Returns the current user's cart or a guest session cart.
        Merging guest -> user carts happens ONCE, at login (see LoginAPIView),
        not here.
        """
        request = self.request

        if request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=request.user)
        else:
            if not request.session.session_key:
                request.session.create()
            cart, _ = Cart.objects.get_or_create(
                session_key=request.session.session_key
            )

        return cart

    def get_queryset(self):
        cart = self.get_or_create_cart()
        return CartItem.objects.filter(cart=cart).select_related(
            "variant", "variant__product"
        )

    def list(self, request, *args, **kwargs):
        cart = self.get_or_create_cart()
        serializer = self.get_serializer(self.get_queryset(), many=True)

        return Response(
            {
                "total_items": cart.total_items,
                "total_price": cart.total_price,
                "items": serializer.data,
            }
        )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        cart = self.get_or_create_cart()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        variant = serializer.validated_data["variant"]
        quantity = serializer.validated_data.get("quantity", 1)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={"quantity": quantity},
        )

        if created:
            if quantity > variant.stock:
                raise ValidationError(f"Only {variant.stock} items left.")
            message = "Item added to cart."
            status_code = status.HTTP_201_CREATED
        else:
            if quantity > variant.stock:
                raise ValidationError(f"Only {variant.stock} items left.")
            cart_item.quantity = quantity
            cart_item.save(update_fields=["quantity"])
            message = "Cart item quantity updated."
            status_code = status.HTTP_200_OK
        response_serializer = self.get_serializer(cart_item)

        return Response(
            {
                "message": message,
                "id": response_serializer.data["id"],
                "total_items": cart.total_items,
                "total_price": cart.total_price,
                "variant": response_serializer.data["variant"],
                "quantity": response_serializer.data["quantity"],
                "unit_price": response_serializer.data["unit_price"],
                "subtotal": response_serializer.data["subtotal"],
            },
            status=status_code,
        )


class CartItemDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = CartItemDetailSerializer
    lookup_field = "public_id"
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return CartItem.objects.filter(cart__user=self.request.user)

        session_key = self.request.session.session_key
        if not session_key:
            return CartItem.objects.none()
        return CartItem.objects.filter(cart__session_key=session_key)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        cart_item = self.get_object()
        serializer = self.get_serializer(cart_item, data=request.data)
        serializer.is_valid(raise_exception=True)

        variant = ProductVariant.objects.get(public_id=cart_item.variant_id)
        quantity = serializer.validated_data["quantity"]

        if quantity > variant.stock:
            raise ValidationError(f"Only {variant.stock} items left.")

        serializer.save()
        response = {
            "message": "Cart item updated successfully.",
            "data": serializer.data,
        }
        return Response(response, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        cart_item = self.get_object()
        cart_item.delete()
        response = {
            "message": "Cart item deleted successfully.",
        }
        return Response(response, status=status.HTTP_200_OK)
