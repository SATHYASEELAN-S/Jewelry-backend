from django.urls import path
from apps.accounts.views import (
    RegisterAPIView,
    LoginAPIView,
    LogoutAPIView,
    AddressAPIView,
    AddressDetailAPIView,
)

urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("address/", AddressAPIView.as_view(), name="address-list"),
    path(
        "address/<uuid:public_id>/",
        AddressDetailAPIView.as_view(),
        name="address-detail",
    ),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("logout/", LogoutAPIView.as_view(), name="login"),
]
