from django.db import transaction

from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .models import Cart, CartItem
from .serializers import CartItemSerializer
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
                "user": request.user.email if request.user.is_authenticated else None,
                "session_key": request.session.session_key,
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
            if (cart_item.quantity + quantity) > variant.stock:
                raise ValidationError(f"Only {variant.stock} items left.")
            cart_item.quantity += quantity
            cart_item.save(update_fields=["quantity"])
            message = "Cart item quantity updated."
            status_code = status.HTTP_200_OK
        response_serializer = self.get_serializer(cart_item)

        return Response(
            {
                "message": message,
                "user": request.user.email if request.user.is_authenticated else None,
                "session_key": request.session.session_key,
                "total_items": cart.total_items,
                "total_price": cart.total_price,
                "variant": response_serializer.data["variant"],
                "quantity": response_serializer.data["quantity"],
                "unit_price": response_serializer.data["unit_price"],
                "subtotal": response_serializer.data["subtotal"],
            },
            status=status_code,
        )


class CartItemDetailAPIVIew(RetrieveAPIView):
    serializer_class = CartItemSerializer
    lookup_field = 'public_id'

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return CartItem.objects.filter(cart__user=self.request.user)
        else:
            return CartItem.objects.filter(cart__session_key=self.request.session.session_key)