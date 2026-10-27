from django.urls import path, include

from apps.products.views import (
    ProductListAPIView,
    ProductDetailAPIView, 
    CategoryListCreateAPIView,
    CategoryDetailAPIView
)

urlpatterns = [
    path("products/", ProductListAPIView.as_view(), name="product-list"),
    path(
        "products/<slug:slug>/", ProductDetailAPIView.as_view(), name="product-detail"
    ),
    path("categories/", CategoryListCreateAPIView.as_view(), name="category-list"), 
    path("category/<slug:slug>/", CategoryDetailAPIView.as_view(), name="category-detail"), 
]
