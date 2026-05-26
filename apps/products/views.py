from django.shortcuts import render


from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.decorators import api_view 
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.products.models import Product, Category
from apps.products.serializers import ProductSerializer, CategorySerializer
from apps.products.pagination import ProductPagination


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
    """
    Returns a list of all jewelry categories.

    Categories:
    - Rings
    - Necklaces
    - Earrings
    - Bracelets
    """
    queryset=Category.objects.all()
    serializer_class=CategorySerializer
    @extend_schema(
        summary     = "List all categories",
        description = "Returns all product categories.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
     
   
    
class ProductDetailAPIView(RetrieveAPIView): 
    """
    Returns full details of a single product by its slug.

    Includes:
    - Product details (name, price, gender, description)
    - Category details
    - All variants (size, stock, extra price)
    - All images
    
    Example:
    - `/api/v1/products/rose-gold-plated-ring/`
    """
    
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
    - `?minprice=100`               → Filter by minimum price
    - `?maxprice=999`               → Filter by maximum price
    - `?minprice=100&maxprice=999`  → Filter by price range
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
            OpenApiParameter('minprice',  description='Minimum price filter (e.g. 100)'),
            OpenApiParameter('maxprice',  description='Maximum price filter (e.g. 999)'),
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
            
        minPrice=self.request.query_params.get('minprice')
        maxPrice=self.request.query_params.get('maxprice')
          
        if minPrice:
            queryset=queryset.filter(price__gte=minPrice)
           
        if maxPrice:
            queryset=queryset.filter(price__lte=maxPrice)        
        

        return queryset