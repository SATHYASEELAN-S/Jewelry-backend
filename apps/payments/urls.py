from django.urls import path

from .views import Home

urlpatterns=[
    path("payments/",Home.as_view(),name="payment")
]