from django.urls import path

from .views import CheckoutAPIView, OrderDetailAPIView, OrderAPIView

urlpatterns = [
    path('orders/checkout/',CheckoutAPIView.as_view(),name="orders-create"),
    path('orders/<uuid:public_id>/',OrderDetailAPIView.as_view(),name="orders-detail"),
    path('orders/',OrderAPIView.as_view(),name="orders-list"),
]
