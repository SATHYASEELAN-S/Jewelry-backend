from django.urls import path

from .views import CartItemAPIView, CartItemDetailAPIVIew

urlpatterns=[ 
    path("items/", CartItemAPIView.as_view(), name="cart-item"),
    path("items/<uuid:public_id>/", CartItemDetailAPIVIew.as_view(), name="cart-item-detail"),

]