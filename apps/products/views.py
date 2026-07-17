from django.shortcuts import render
from django.http import Http404
 

from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.decorators import api_view 
from rest_framework.filters import SearchFilter,OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.exceptions import NotFound

from apps.products.models import Product, Category
from apps.products.serializers import ProductSerializer, CategorySerializer
from apps.products.pagination import ProductPagination
from apps.products.filters import ProductFilter

@api_view(["GET"])
def home(request):
    return Response({
        "message": "Jewelry API is running",
        "admin": request.build_absolute_uri("/admin/"),
        "products": request.build_absolute_uri("/api/v1/products/"),
        "categories": request.build_absolute_uri("/api/v1/categories/"),
        "swagger_docs": request.build_absolute_uri("/api/v1/docs/"),
        "redoc": request.build_absolute_uri("/api/v1/redoc/"),
    })



class CategoryListAPIView(ListAPIView):
    
    queryset=Category.objects.all()
    serializer_class=CategorySerializer
    
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)  
    
class ProductDetailAPIView(RetrieveAPIView): 
    
    serializer_class=ProductSerializer
    lookup_field='slug'
    
    def get_queryset(self):
        return Product.objects.filter(is_available=True)\
            .select_related('category')\
            .prefetch_related('variants', 'images')
            
    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            raise NotFound("Product not found.")
    
class ProductListAPIView(ListAPIView):
    
    serializer_class = ProductSerializer
    pagination_class = ProductPagination
    filterset_class  = ProductFilter
    filter_backends  = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields    = ['name', 'description']
    ordering_fields  = ['price','created_at']
    
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        show_all=self.request.query_params.get('show_all')
        if show_all:
            return Product.objects.all()\
                .select_related('category')\
                    .prefetch_related('variants','images')\
                        .order_by('created_at')
                
        return Product.objects.filter(is_available=True)\
            .select_related('category')\
                .prefetch_related('variants', 'images')\
                    .order_by('created_at')  
            