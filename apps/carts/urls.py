from django.urls import path

from .views import Home

urlpatterns=[
    path("carts/",Home.as_view(),name="carts")
]