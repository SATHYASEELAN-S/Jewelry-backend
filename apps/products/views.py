from django.shortcuts import get_object_or_404, render
from django.db.models import ProtectedError, RestrictedError

from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import AllowAny, IsAdminUser, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from apps.products.models import Product, Category, ProductImage
from apps.products.serializers import (
    ProductSerializer,
    ProductWriteSerializer,
    CategorySerializer,
    CategoryCreateSerializer,
    ProductImageSerializer,
)
from apps.products.pagination import ProductPagination
from apps.products.filters import ProductFilter

from apps.common.exceptions import ResourceInUseError
from .cache_utils import *
from .signals import _invalidate

@api_view(["GET"])
def home(request):
    return Response(
        {
            "message": "Jewelry API is running",
            "admin": request.build_absolute_uri("/admin/"),
            "products": request.build_absolute_uri("/api/v1/products/"),
            "categories": request.build_absolute_uri("/api/v1/categories/"),
            "swagger_docs": request.build_absolute_uri("/api/v1/docs/"),
            "redoc": request.build_absolute_uri("/api/v1/redoc/"),
        }
    )


def product_queryset(user):
    query = (
        Product.objects.select_related("category")
        .prefetch_related("variants", "images")
        .order_by("created_at")
    )

    if user.is_staff:
        return query
    return query.filter(is_available=True)

class PublicReadAdminWriteMixin:
    """Anyone can read; only admin users can create, update or delete."""

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsAdminUser()]


class CategoryListCreateAPIView(PublicReadAdminWriteMixin, ListCreateAPIView):
    queryset = Category.objects.all()

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return CategoryCreateSerializer
        return CategorySerializer


class CategoryDetailAPIView(PublicReadAdminWriteMixin, RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return CategoryCreateSerializer
        return CategorySerializer

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        count = category.products.count()

        try:
            category.delete()
        except (ProtectedError, RestrictedError) as e:
            raise ResourceInUseError(
                f"Cannot delete '{category.name}' because it has "
                f"{count} product(s). Move or delete them first."
            ) from e

        return Response(status=204)


class ProductDetailAPIView(PublicReadAdminWriteMixin, RetrieveUpdateDestroyAPIView):
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return ProductSerializer
        return ProductWriteSerializer

    def get_queryset(self):
        return product_queryset(self.request.user)

    def retrieve(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super().retrieve(request, *args, **kwargs)
        
        key = detail_cache_key(kwargs["slug"])

        data = safe_get(key)
        if data is not None:
            return Response(data)

        response = super().retrieve(request, *args, **kwargs)
        safe_set(key, response.data, with_jitter(DETAIL_TTL))
        return response
    
    def perform_update(self, serializer):
        old_slug = serializer.instance.slug 
        serializer.save()
        _invalidate([old_slug])
        
    def perform_destroy(self, instance):
        slug = instance.slug
        try:
            instance.delete()
        except (ProtectedError, RestrictedError) as e:
            raise ResourceInUseError(
                f"Cannot delete '{instance.name}' because it is used by other records "
                f"(for example orders). Mark it unavailable instead."
            ) from e
        
        _invalidate(slug)

class ProductListAPIView(PublicReadAdminWriteMixin, ListCreateAPIView):
    pagination_class = ProductPagination
    filterset_class = ProductFilter
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["price", "created_at"]

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return ProductSerializer
        return ProductWriteSerializer

    def get_queryset(self):
        return product_queryset(self.request.user)

    def list(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super().list(request, *args, **kwargs)
 
        key = list_cache_key(request)
        data = safe_get(key)
        if data is not None:
            return Response(data)

        response = super().list(request, *args, **kwargs)
        safe_set(key, response.data, with_jitter(LIST_TTL))
        return response

class ProductImageListCreateAPIView(ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = ProductImageSerializer  

    def get_queryset(self):
        product = get_object_or_404(Product, slug=self.kwargs["slug"])
        return ProductImage.objects.filter(product=product)

    def perform_create(self, serializer):
        product = get_object_or_404(Product, slug=self.kwargs["slug"])
        serializer.save(product=product)
    
 
class ProductImageDetailAPIView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = ProductImageSerializer
    lookup_field = "public_id"
    
    def get_queryset(self):
        # Only images belonging to THIS product
        return ProductImage.objects.filter(product__slug=self.kwargs["slug"])