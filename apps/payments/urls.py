from django.urls import path

from .views import InitiatePaymentAPIView, RazorpayWebhookAPIView

urlpatterns=[
    path("",InitiatePaymentAPIView.as_view(),name="payment"),
    path("webhook/", RazorpayWebhookAPIView.as_view(), name="razorpay-webhook"),
]