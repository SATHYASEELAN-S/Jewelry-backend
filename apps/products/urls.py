from django.urls import path, include

from apps.products.views import (
    ProductListAPIView,
    ProductDetailAPIView, 
    ProductImageListCreateAPIView,
    ProductImageDetailAPIView,
    CategoryListCreateAPIView,
    CategoryDetailAPIView,
)

urlpatterns = [
    path("products/", ProductListAPIView.as_view(), name="product-list"),
    path(
        "products/<slug:slug>/", ProductDetailAPIView.as_view(), name="product-detail"
    ),
    path("products/<slug:slug>/images/", ProductImageListCreateAPIView.as_view()),
    path("products/<slug:slug>/images/<uuid:public_id>/", ProductImageDetailAPIView.as_view()),
    path("categories/", CategoryListCreateAPIView.as_view(), name="category-list"), 
    path("category/<slug:slug>/", CategoryDetailAPIView.as_view(), name="category-detail"), 
]
