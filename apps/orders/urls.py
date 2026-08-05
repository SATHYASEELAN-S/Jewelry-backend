from django.urls import path

from .views import CheckoutAPIView, OrderAPIView,  OrderDetailAPIView

urlpatterns = [
    path('orders/checkout/', CheckoutAPIView.as_view(), name="orders-create"),
    path('orders/', OrderAPIView.as_view(), name="orders-list"),
    path('orders/<uuid:public_id>/', OrderDetailAPIView.as_view(), name="orders-detail"),
]