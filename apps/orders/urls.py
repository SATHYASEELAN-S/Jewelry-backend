from django.urls import path

from .views import home
urlpatterns = [
    path('orders/',home.as_view(),name="orders"),
]
