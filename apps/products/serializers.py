from apps.products.models import Product, ProductVariant, ProductImage, Category

from rest_framework import serializers


class CategorySerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug"]

class CategoryCreateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = Category
        fields = "__all__"


class ProductVariantSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    is_in_stock = serializers.ReadOnlyField()

    class Meta:
        model = ProductVariant
        fields = ["id", "size", "stock", "extra_price", "is_in_stock"]


class ProductImageSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "is_primary"]


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "name",
            "slug",
            "description",
            "price",
            "gender",
            "is_featured",
            "category",
            "variants",
            "images",
            "created_at",
        ]
