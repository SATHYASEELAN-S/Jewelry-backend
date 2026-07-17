from django.contrib.auth import authenticate
from django.db import transaction

from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListCreateAPIView
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.exceptions import ValidationError

from apps.accounts.models import Address
from apps.accounts.serializers import (
    RegisterSerializer,
    LoginSerializer,
    LogoutSerializer,
    AddressSerializer,
)


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        results = {
            "message": "Registered Successfully.",
            "refresh token": str(refresh),
            "access token": str(refresh.access_token),
        }

        return Response(results, status=status.HTTP_201_CREATED)


from rest_framework.exceptions import AuthenticationFailed


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(request, email=email, password=password)

        if not user:
            raise AuthenticationFailed()

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "Login Successfully.",
                "refresh token": str(refresh),
                "access token": str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refresh_token = serializer.validated_data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            raise ValidationError("Invalid refresh token")

        return Response({"message": "logout successfully"}, status=status.HTTP_200_OK)


class AddressAPIView(ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user).order_by(
            "-is_default", "-id"
        )

    @transaction.atomic
    def perform_create(self, serializer):
        is_default = serializer.validated_data.get("is_default", False)

        if is_default:
            Address.objects.filter(
                user=self.request.user, is_default=is_default
            ).update(is_default=False)

        elif (
            not Address.objects.select_for_update()
            .filter(user=self.request.user, is_default=True)
            .exists()
        ):
            is_default = True

        serializer.save(user=self.request.user, is_default=is_default)


class AddressDetailAPIView(APIView):

    def get(self, request):
        pass
