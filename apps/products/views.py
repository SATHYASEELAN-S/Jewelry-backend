from django.shortcuts import render


from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.decorators import api_view

from apps.products.models import Product, Category
from apps.products.serializers import ProductSerializer, CategorySerializer
from apps.products.pagination import ProductPagination
from apps.products.filters import ProductFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .cache_utils import *

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


class CategoryListAPIView(ListAPIView):

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ProductDetailAPIView(RetrieveAPIView):
    serializer_class = ProductSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Product.objects.all()
            .select_related("category")
            .prefetch_related("variants", "images")
        )

    def retrieve(self, request, *args, **kwargs):
        key = detail_cache_key(kwargs["slug"])
       
        data = safe_get(key)
        if data is not None:
            return Response(data)

        response = super().retrieve(request, *args, **kwargs)
        safe_set(key, response.data, with_jitter(DETAIL_TTL))
        return response


class ProductListAPIView(ListAPIView):
    serializer_class = ProductSerializer
    pagination_class = ProductPagination
    filterset_class = ProductFilter
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["price", "created_at"]

    def get_queryset(self):
        # show_all = self.request.query_params.get("show_all")
        # if show_all:
        #     return (
        #         Product.objects.all()
        #         .select_related("category")
        #         .prefetch_related("variants", "images")
        #         .order_by("created_at")
        #     )

        return (
            Product.objects.filter(is_available=True)
            .select_related("category")
            .prefetch_related("variants", "images")
            .order_by("created_at")
        )
    
    def list(self, request, *args, **kwargs):
        key = list_cache_key(request)
        data = safe_get(key)
        if data is not None:
            return Response(data)

        response = super().list(request, *args, **kwargs)
        safe_set(key, response.data, with_jitter(LIST_TTL))
        return response
