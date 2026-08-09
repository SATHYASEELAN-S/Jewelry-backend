from django.urls import path

from .views import CartItemAPIView, CartItemDetailAPIView

urlpatterns = [
    path("items/", CartItemAPIView.as_view(), name="cart-item"),
    path(
        "items/<uuid:public_id>/",
        CartItemDetailAPIView.as_view(),
        name="cart-item-detail",
    ),
]
