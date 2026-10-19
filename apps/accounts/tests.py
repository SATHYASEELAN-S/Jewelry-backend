import uuid
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from unittest.mock import patch

from apps.accounts.models import Address

User = get_user_model()


class TestRegisterAPI(APITestCase):

    def setUp(self):
        # Replace the Celery task so no broker is needed.
        patcher = patch("apps.accounts.views.send_welcome_email")
        self.mock_email = patcher.start()
        self.addCleanup(patcher.stop)

        self.url = reverse("register")
        self.payload = {
            "email": "sathya@example.com",
            "first_name": "Sathya",
            "last_name": "S",
            "phone_number": "9874651230",
            "password": "StrongPass@123",
            "confirm_password": "StrongPass@123",
        }

    def test_register_success(self):
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["message"], "Registered Successfully.")
        self.assertIn("access token", response.data)
        self.assertIn("refresh token", response.data)

    def test_register_creates_user_with_hashed_password(self):
        self.client.post(self.url, self.payload, format="json")

        user = User.objects.get(email=self.payload["email"])
        self.assertNotEqual(user.password, self.payload["password"])
        self.assertTrue(user.check_password(self.payload["password"]))

    def test_register_does_not_leak_password(self):
        response = self.client.post(self.url, self.payload, format="json")
        self.assertNotIn("password", response.data)

    def test_register_sends_welcome_email(self):
        self.client.post(self.url, self.payload, format="json")

        self.mock_email.delay.assert_called_once_with(
            self.payload["email"], self.payload["first_name"]
        )

    def test_register_duplicate_email_returns_400(self):
        self.client.post(self.url, self.payload, format="json")
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.filter(email=self.payload["email"]).count(), 1)

    def test_register_missing_fields_returns_400(self):
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0)
        self.mock_email.delay.assert_not_called()

    def test_register_invalid_email_returns_400(self):
        self.payload["email"] = "not-an-email"
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 400)

    def test_register_weak_password_returns_400(self):
        self.payload["password"] = "pass"
        self.payload["confirm_password"] = "pass"
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 400) 
        self.assertEqual(User.objects.count(), 0)

    def test_register_password_mismatch_returns_400(self):
        self.payload["password"] = "Password@123"
        self.payload["confirm_password"] = "StrongPass@123"
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0)


class TestLoginAPI(APITestCase):
    def setUp(self):
        # Replace the cart merge so these tests only cover login.
        patcher = patch("apps.accounts.views.merge_guest_cart_into_user_cart")
        self.mock_merge = patcher.start()
        self.addCleanup(patcher.stop)

        self.url = reverse("login")
        self.password = "StrongPass@123"
        self.user = User.objects.create_user(
            email="sathya@example.com",
            password=self.password,
            first_name="Sathya",
            last_name="S",
            phone_number="9876543210",
        )
        self.payload = {"email": self.user.email, "password": self.password}

    def test_login_success(self):
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Login Successfully.")
        self.assertIn("access token", response.data)
        self.assertIn("refresh token", response.data)

    def test_login_merges_guest_cart(self):
        self.client.post(self.url, self.payload, format="json")

        self.mock_merge.assert_called_once()
        # the second argument is the logged-in user
        self.assertEqual(self.mock_merge.call_args.args[1], self.user)

    def test_login_wrong_password_returns_401(self):
        self.payload["password"] = "WrongPass@123"
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("access token", response.data)
        self.mock_merge.assert_not_called()

    def test_login_unknown_email_returns_401(self):
        self.payload["email"] = "nobody@example.com"
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 401)
        self.mock_merge.assert_not_called()

    def test_login_errors_do_not_reveal_which_part_was_wrong(self):
        wrong_pw = self.client.post(
            self.url, {**self.payload, "password": "WrongPass@123"}, format="json"
        )
        no_user = self.client.post(
            self.url, {**self.payload, "email": "nobody@example.com"}, format="json"
        )

        self.assertEqual(wrong_pw.data, no_user.data)

    def test_login_inactive_user_returns_401(self):
        self.user.is_active = False
        self.user.save()

        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 401)

    def test_login_missing_fields_returns_400(self):
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.mock_merge.assert_not_called()


class TestLogoutAPI(APITestCase):
    def setUp(self):
        self.url = reverse("logout")
        self.user = User.objects.create_user(
            email="sathya@example.com",
            password="StrongPass@123",
            first_name="Sathya",
        )
        self.refresh = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.refresh.access_token}"
        )

    def test_logout_success(self):
        response = self.client.post(
            self.url, {"refresh_token": str(self.refresh)}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "logout successfully")

    def test_logout_blacklists_refresh_token(self):
        self.client.post(self.url, {"refresh_token": str(self.refresh)}, format="json")

        self.assertTrue(
            BlacklistedToken.objects.filter(token__jti=self.refresh["jti"]).exists()
        )

    def test_logout_same_token_twice_returns_400(self):
        data = {"refresh_token": str(self.refresh)}
        self.client.post(self.url, data, format="json")
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 400)

    def test_logout_invalid_token_returns_400(self):
        response = self.client.post(
            self.url, {"refresh_token": "not-a-real-token"}, format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_logout_missing_token_returns_400(self):
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, 400)

    def test_logout_requires_authentication(self):
        self.client.credentials()  # remove the Authorization header
        response = self.client.post(
            self.url, {"refresh_token": str(self.refresh)}, format="json"
        )

        self.assertEqual(response.status_code, 401)
        self.assertFalse(BlacklistedToken.objects.exists())

def make_user(email, first_name="User"):
    return User.objects.create_user(
        email=email, password="StrongPass@123", first_name=first_name
    )

def make_address(user, **overrides):
    data = {
        "user": user,
        "street": "12 Main Street",
        "landmark": "Near Temple",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "pincode": "600001",
        "is_default": False,
    }
    data.update(overrides)
    return Address.objects.create(**data)


class TestAddressListCreateAPI(APITestCase):
    def setUp(self):
        self.url = reverse("address-list")
        self.user = make_user("sathya@example.com")
        self.other = make_user("other@example.com")
        self.client.force_authenticate(user=self.user)
        self.payload = {
            "street": "12 Main Street",
            "landmark": "Near Temple",
            "city": "Chennai",
            "state": "Tamil Nadu",
            "pincode": "600001",
        }

    # ---------- auth ----------

    def test_list_requires_authentication(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_create_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Address.objects.count(), 0)

     # ---------- list ----------

    def test_list_returns_only_own_addresses(self):
        make_address(self.user)
        make_address(self.other, street="Someone else's street")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["street"], "12 Main Street")

    def test_list_puts_default_address_first(self):
        make_address(self.user, street="Old default", is_default=True)
        make_address(self.user, street="Newer, not default")

        response = self.client.get(self.url)

        streets = [a["street"] for a in response.data["results"]]
        self.assertEqual(streets, ["Old default", "Newer, not default"])

    def test_list_empty_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0) 

    # ---------- create ----------

    def test_create_success(self):
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["message"], "Address created successfully")
        self.assertEqual(response.data["city"], "Chennai")
        self.assertTrue(Address.objects.filter(user=self.user).exists())

    def test_create_assigns_address_to_logged_in_user(self):
        self.payload["user"] = self.other.id  # must be ignored
        self.client.post(self.url, self.payload, format="json")

        self.assertEqual(Address.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Address.objects.filter(user=self.other).count(), 0)

    def test_first_address_becomes_default_automatically(self):
        response = self.client.post(self.url, self.payload, format="json")
        self.assertTrue(response.data["is_default"])

    def test_second_address_is_not_default(self):
        make_address(self.user, is_default=True)

        response = self.client.post(self.url, self.payload, format="json")

        self.assertFalse(response.data["is_default"])
        self.assertEqual(Address.objects.filter(user=self.user, is_default=True).count(), 1)

    def test_create_with_is_default_replaces_old_default(self):
        old = make_address(self.user, is_default=True)
        self.payload["is_default"] = True

        response = self.client.post(self.url, self.payload, format="json")

        old.refresh_from_db()
        self.assertEqual(response.status_code, 201)
        self.assertFalse(old.is_default)
        self.assertEqual(Address.objects.filter(user=self.user, is_default=True).count(), 1)

    def test_other_users_default_is_untouched_on_create(self):
        theirs = make_address(self.other, is_default=True)
        self.payload["is_default"] = True

        self.client.post(self.url, self.payload, format="json")

        theirs.refresh_from_db()
        self.assertTrue(theirs.is_default)

    def test_create_missing_fields_returns_400(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Address.objects.count(), 0)


class TestAddressDetailAPI(APITestCase):
    def setUp(self):
        self.user = make_user("sathya@example.com")
        self.other = make_user("other@example.com")
        self.client.force_authenticate(user=self.user)

        self.default = make_address(self.user, street="Default street", is_default=True)
        self.second = make_address(self.user, street="Second street")
        self.theirs = make_address(self.other, street="Their street", is_default=True)

    def url(self, address):
        return reverse("address-detail", kwargs={"public_id": address.public_id})

    # ---------- auth / ownership ----------

    def test_detail_requires_authentication(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.url(self.default)).status_code, 401)

    def test_cannot_read_another_users_address(self):
        self.assertEqual(self.client.get(self.url(self.theirs)).status_code, 404)

    def test_cannot_update_another_users_address(self):
        response = self.client.patch(self.url(self.theirs), {"city": "Hacked"}, format="json")

        self.theirs.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertNotEqual(self.theirs.city, "Hacked")

    def test_cannot_delete_another_users_address(self):
        response = self.client.delete(self.url(self.theirs))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Address.objects.filter(pk=self.theirs.pk).exists())

    def test_unknown_public_id_returns_404(self):
        url = reverse("address-detail", kwargs={"public_id": uuid.uuid4()})
        self.assertEqual(self.client.get(url).status_code, 404)

    # ---------- retrieve ----------

    def test_retrieve_own_address(self):
        response = self.client.get(self.url(self.default))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["street"], "Default street")

    # ---------- update ----------

    def test_patch_updates_field(self):
        response = self.client.patch(self.url(self.second), {"city": "Madurai"}, format="json")

        self.second.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.second.city, "Madurai")

    def test_patch_without_is_default_leaves_default_untouched(self):
        self.client.patch(self.url(self.default), {"city": "Madurai"}, format="json")

        self.default.refresh_from_db()
        self.assertTrue(self.default.is_default)

    def test_patch_is_default_true_moves_the_default(self):
        response = self.client.patch(self.url(self.second), {"is_default": True}, format="json")

        self.default.refresh_from_db()
        self.second.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.second.is_default)
        self.assertFalse(self.default.is_default)

    def test_patch_is_default_true_does_not_touch_other_users(self):
        self.client.patch(self.url(self.second), {"is_default": True}, format="json")

        self.theirs.refresh_from_db()
        self.assertTrue(self.theirs.is_default)

    def test_cannot_unset_default_directly(self):
        response = self.client.patch(self.url(self.default), {"is_default": False}, format="json")

        self.default.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertTrue(self.default.is_default)

    # ---------- delete ----------

    def test_delete_non_default_address(self):
        response = self.client.delete(self.url(self.second))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Address.objects.filter(pk=self.second.pk).exists())

    def test_cannot_delete_default_address(self):
        response = self.client.delete(self.url(self.default))

        self.assertEqual(response.status_code, 400)
        self.assertTrue(Address.objects.filter(pk=self.default.pk).exists())


class TestProfileAPI(APITestCase):
    def setUp(self):
        self.url = reverse("profile-list")
        self.user = make_user("sathya@example.com", first_name="Sathya")
        self.other = make_user("other@example.com", first_name="Other")
        self.client.force_authenticate(user=self.user)

    def test_profile_requires_authentication(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_get_returns_logged_in_users_profile(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "sathya@example.com")
        self.assertEqual(response.data["first_name"], "Sathya")

    def test_get_does_not_expose_password(self):
        response = self.client.get(self.url)
        self.assertNotIn("password", response.data)

    def test_patch_updates_own_profile(self):
        response = self.client.patch(self.url, {"first_name": "Updated"}, format="json")

        self.user.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.first_name, "Updated")

    def test_patch_does_not_change_other_users(self):
        self.client.patch(self.url, {"first_name": "Updated"}, format="json")

        self.other.refresh_from_db()
        self.assertEqual(self.other.first_name, "Other")
        
    def test_patch_cannot_change_email(self):
        self.client.patch(self.url, {"email": "sathya@update.com"}, format="json")

        self.user.refresh_from_db()
        self.assertNotEqual(self.user.email, "sathya@update.com")

    def test_patch_cannot_make_user_staff(self):
        self.client.patch(self.url, {"is_staff": True, "is_superuser": True}, format="json")

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_patch_cannot_change_password_through_profile(self):
        self.client.patch(self.url, {"password": "Hacked@123"}, format="json")

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("StrongPass@123"))