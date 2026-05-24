 
from django.urls import path,include
 
from apps.products.views import  ProductListAPIView,CategoryListAPIView,ProductDetailAPIView

urlpatterns = [
    path('products/', ProductListAPIView.as_view(), name='product-list'),
    path('products/<slug:slug>/', ProductDetailAPIView.as_view(), name='product-detail'),
    path('categories/',           CategoryListAPIView.as_view(),  name='category-list'),
]