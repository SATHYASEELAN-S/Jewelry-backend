from django.shortcuts import render


from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.products.models import Product, Category
from apps.products.serializers import ProductSerializer, CategorySerializer
from apps.products.pagination import ProductPagination

class CategoryListAPIView(ListAPIView):
    queryset=Category.objects.all()
    serializer_class=CategorySerializer
    @extend_schema(
        summary     = "List all categories",
        description = "Returns all product categories.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
     
   
    
class ProductDetailAPIView(RetrieveAPIView): 
    serializer_class=ProductSerializer
    lookup_field='slug'
    @extend_schema(
        summary     = "Get product detail",
        description = "Returns a single product detail by slug.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
        
    def get_queryset(self):
        return Product.objects.filter(is_available=True)\
            .select_related('category')\
            .prefetch_related('variants', 'images')
    
    
class ProductListAPIView(ListAPIView):
    """
    Returns a list of all available products.
    
    Filters:
    - `?gender=female` → Filter by gender (male, female, unisex)
    - `?category=rings` → Filter by category slug
    - `?featured=true` → Get featured products only
    - `?page=2` → Pagination
        - `?page_size=20` → Change number of items per page (max 50)
    """
    
    @extend_schema(
        summary     = "List all products",
        description = "Returns all available products. Supports filtering by gender, category and featured.",
        parameters  = [
            OpenApiParameter('gender',   description='Filter by gender (male, female, unisex)'),
            OpenApiParameter('category', description='Filter by category slug'),
            OpenApiParameter('featured', description='Filter featured products (true/false)'),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    
    serializer_class = ProductSerializer
    pagination_class = ProductPagination

    def get_queryset(self):
        queryset = Product.objects.filter(is_available=True)\
            .select_related('category')\
                .prefetch_related('variants', 'images')

        # filter by gender → /api/v1/products/?gender=female
        gender = self.request.query_params.get('gender')
        if gender:
            queryset = queryset.filter(gender=gender)

        # filter by category → /api/v1/products/?category=rings
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)

        # filter featured → /api/v1/products/?featured=true
        featured = self.request.query_params.get('featured')
        if featured:
            queryset = queryset.filter(is_featured=True)

        return queryset