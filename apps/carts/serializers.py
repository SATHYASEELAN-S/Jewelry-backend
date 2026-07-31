from rest_framework import serializers
from .models import Cart, CartItem


class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = ["user", "session_key", "total_items", "total_price"]
        read_only_fields = ["user", "session_key", "total_items", "total_price"]


class CartItemSerializer(serializers.ModelSerializer):
    unit_price = serializers.ReadOnlyField()
    subtotal = serializers.ReadOnlyField()
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "variant", "quantity", "unit_price", "subtotal"]
        read_only_fields = ["cart"]


class CartItemDetailSerializer(serializers.ModelSerializer):
    unit_price = serializers.ReadOnlyField()
    subtotal = serializers.ReadOnlyField()
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "variant", "quantity", "unit_price", "subtotal"]
        read_only_fields = ["variant"]
        extra_kwargs = {
            "quantity": {"required": True},
        }

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value
