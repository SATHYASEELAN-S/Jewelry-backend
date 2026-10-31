from django.db import transaction

from rest_framework import serializers

from apps.products.models import Product, ProductVariant, ProductImage, Category


class CategorySerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug"]

class CategoryCreateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "image",
            "alt_text",
            "description",
            "created_at",
        ]


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


class ProductVariantWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ["size", "stock", "extra_price"]
        extra_kwargs = {
            "size": {"required": True},
            "stock": {"required": True},
            "extra_price": {"required": True},
        }


class ProductWriteSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.all()
    )

    variants = ProductVariantWriteSerializer(many=True, allow_empty=False)

    class Meta:
        model = Product
        fields = [
            "name",
            "slug",
            "description",
            "price",
            "gender",
            "is_featured",
            "is_available",
            "category",
            "variants",
        ]

    def create(self, validated_data):
        variants = validated_data.pop("variants")

        with transaction.atomic():
            product = Product.objects.create(**validated_data)
            ProductVariant.objects.bulk_create(
                [ProductVariant(product=product, **variant) for variant in variants]
            )

        return product

    def update(self, instance, validated_data):
        variants = validated_data.pop("variants", None)

        with transaction.atomic():
            for field, value in validated_data.items():
                setattr(instance, field, value)
            instance.save()

            if variants is not None:
                self._sync_variants(instance, variants)

        return instance
    
    def _sync_variants(self, product, variants):
        """
        Match variants by size, so existing variants keep their id/public_id
        (orders and carts point to them):
          - size already exists  -> update stock / extra_price
          - new size             -> create it
          - size left out        -> delete it, unless orders use it
        """
        existing = {v.size: v for v in product.variants.all()}
        sent_sizes = set()
 
        for data in variants:
            sent_sizes.add(data["size"])
            variant = existing.get(data["size"])
            if variant:
                variant.stock = data["stock"]
                variant.extra_price = data["extra_price"]
                variant.save()
            else:
                ProductVariant.objects.create(product=product, **data)
 
        for size, variant in existing.items():
            if size in sent_sizes:
                continue
            if variant.order_items.exists():
                # Raising inside transaction.atomic() undoes the whole update
                raise serializers.ValidationError({
                    "variants": f"Size '{size}' is used by orders and can't be removed. "
                                f"Set its stock to 0 instead."
                })
            variant.delete()

    def to_representation(self, instance):
        return ProductSerializer(instance, context=self.context).data