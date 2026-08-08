from rest_framework import serializers
from .models import Order, OrderItem, OrderStatusHistory


class OrderItemSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    variant = serializers.UUIDField(source="variant.public_id", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    size = serializers.CharField(source="variant.size", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "variant",
            "product_name",
            "size",
            "quantity",
            "unit_price",
            "subtotal",
        ]
        read_only_fields = fields

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = OrderStatusHistory
        fields = ["id", "status", "changed_at"]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    status = serializers.CharField(read_only=True)
    class Meta:
        model = Order
        fields = [
            "id", "order_number","status",
            "shipping_street", "shipping_city", "shipping_state",
            "shipping_pincode", "shipping_landmark",
            "total_price", "created_at", "items", "status_history",
        ]
        read_only_fields = fields  

 
class OrderCancelSerializer(serializers.Serializer):
    cancel = serializers.BooleanField()