from django.contrib.auth import authenticate
from django.db import transaction
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


from apps.accounts.permissions import AddressDetailPermission
from apps.accounts.pagination import AddressPagination
from apps.accounts.throttling import RegisterThrottle
from apps.accounts.models import Address
from apps.accounts.serializers import (
    AddressSerializer,
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    ProfileSerializer,
)
from apps.accounts.tasks import send_welcome_email

User = get_user_model()

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]
    # throttle_classes=[RegisterThrottle,]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        send_welcome_email.delay(user.email, user.first_name)
        results = {
            "message": "Registered Successfully.",
            "refresh token": str(refresh),
            "access token": str(refresh.access_token),
        }

        return Response(results, status=status.HTTP_201_CREATED)


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
    pagination_class = AddressPagination

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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        print(serializer.data)
        response = {
            "message": "Address created successfully",
            "id": serializer.data["id"],
            "street": serializer.data["street"],
            "landmark": serializer.data["landmark"],
            "city": serializer.data["city"],
            "state": serializer.data["state"],
            "pincode": serializer.data["pincode"],
            "is_default": serializer.data["is_default"],
        }
        return Response(response, status=status.HTTP_201_CREATED)


class AddressDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated, AddressDetailPermission]
    lookup_field = "public_id"

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    @transaction.atomic
    def perform_update(self, serializer):
        is_default = serializer.validated_data.get("is_default", None)

        # Only act if the client explicitly included is_default in the request
        if is_default is True:
            Address.objects.select_for_update().filter(
                user=self.request.user, is_default=True
            ).exclude(pk=self.get_object().pk).update(is_default=False)
            serializer.save()

        elif is_default is False:
            raise ValidationError(
                "You can't unset the default address directly. Set another address as default instead."
            )

        else:
            # is_default wasn't part of this update at all — leave it untouched
            serializer.save()

    def perform_destroy(self, instance):
        if instance.is_default:
            raise ValidationError(
                "You can't delete the default address. Set another address as default first."
            )
        return super().perform_destroy(instance)


class ProfileAPIView(RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj = self.request.user
        self.check_object_permissions(self.request, obj)
        return obj
