import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.carts.models import Cart, CartItem
from apps.products.models import Category, Product, ProductVariant

User = get_user_model()


def make_user(email):
    return User.objects.create_user(
        email=email, password="StrongPass@123", first_name="User"
    )


def make_product(slug="gold-ring", price=Decimal("500.00")):
    category, _ = Category.objects.get_or_create(name="Rings", slug="rings")
    return Product.objects.create(
        category=category,
        name=slug,
        slug=slug,
        description="A ring",
        price=price,
        gender="female",
        is_available=True,
    )


def make_variant(product, stock=5, extra_price=Decimal("50.00"), **extra):
    # add any other required ProductVariant fields (size, sku, ...) via **extra
    return ProductVariant.objects.create(
        product=product, stock=stock, extra_price=extra_price, **extra
    )


class CartTestBase(APITestCase):
    def setUp(self):
        self.list_url = reverse("cart-item")
        self.user = make_user("sathya@example.com")
        self.other = make_user("other@example.com")
        self.product = make_product()
        self.variant = make_variant(self.product, stock=5)  # unit price 550.00

    def detail_url(self, item):
        return reverse("cart-item-detail", kwargs={"public_id": item.public_id})

    def add_payload(self, variant=None, quantity=1):
        variant = variant or self.variant
        return {"variant": str(variant.public_id), "quantity": quantity}


class TestCartListAPI(CartTestBase):
    def test_empty_cart_for_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_items"], 0)
        self.assertEqual(response.data["total_price"], 0)
        self.assertEqual(response.data["items"], [])

    def test_empty_cart_for_guest(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["items"], [])

    def test_list_returns_items_and_totals(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, variant=self.variant, quantity=2)
        other_variant = make_variant(
            make_product("silver-ring", Decimal("100.00")), extra_price=Decimal("0.00")
        )
        CartItem.objects.create(cart=cart, variant=other_variant, quantity=1)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url)

        self.assertEqual(response.data["total_items"], 3)
        self.assertEqual(response.data["total_price"], Decimal("1200.00"))  # 2*550 + 100
        self.assertEqual(len(response.data["items"]), 2)

    def test_list_shows_only_own_items(self):
        CartItem.objects.create(
            cart=Cart.objects.create(user=self.other), variant=self.variant
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.list_url)

        self.assertEqual(response.data["items"], [])

    def test_guest_cannot_see_user_cart(self):
        CartItem.objects.create(
            cart=Cart.objects.create(user=self.user), variant=self.variant
        )
        response = self.client.get(self.list_url)
        self.assertEqual(response.data["items"], [])

    def test_two_guests_have_separate_carts(self):
        guest_a, guest_b = APIClient(), APIClient()
        guest_a.post(self.list_url, self.add_payload(), format="json")

        response = guest_b.get(self.list_url)

        self.assertEqual(response.data["items"], [])


class TestCartCreateAPI(CartTestBase):
    def test_add_item_as_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.list_url, self.add_payload(quantity=2), format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["message"], "Item added to cart.")
        self.assertEqual(response.data["quantity"], 2)
        self.assertEqual(response.data["unit_price"], Decimal("550.00"))
        self.assertEqual(response.data["subtotal"], Decimal("1100.00"))
        self.assertEqual(response.data["total_items"], 2)
        self.assertEqual(CartItem.objects.filter(cart__user=self.user).count(), 1)

    def test_add_item_as_guest_creates_session_cart(self):
        response = self.client.post(self.list_url, self.add_payload(), format="json")

        self.assertEqual(response.status_code, 201)
        cart = Cart.objects.get()
        self.assertIsNone(cart.user)
        self.assertTrue(cart.session_key)

    def test_guest_cart_persists_across_requests(self):
        self.client.post(self.list_url, self.add_payload(), format="json")

        response = self.client.get(self.list_url)

        self.assertEqual(len(response.data["items"]), 1)

    def test_quantity_defaults_to_one(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.list_url, {"variant": str(self.variant.public_id)}, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["quantity"], 1)

    def test_user_gets_one_cart_only(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(self.list_url, self.add_payload(), format="json")
        self.client.post(self.list_url, self.add_payload(), format="json")

        self.assertEqual(Cart.objects.filter(user=self.user).count(), 1)

    def test_changing_same_variant_quantity(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(self.list_url, self.add_payload(quantity=2), format="json")

        response = self.client.post(self.list_url, self.add_payload(quantity=1), format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Cart item quantity updated.")
        self.assertEqual(response.data["quantity"], 1)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_add_more_than_stock_returns_400_and_creates_nothing(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.list_url, self.add_payload(quantity=6), format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(CartItem.objects.count(), 0)  # atomic rolled it back

    def test_increase_beyond_stock_returns_400_and_keeps_quantity(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(self.list_url, self.add_payload(quantity=4), format="json")

        response = self.client.post(self.list_url, self.add_payload(quantity=6), format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(CartItem.objects.get().quantity, 4)

    def test_out_of_stock_variant_returns_400(self):
        empty = make_variant(make_product("sold-out"), stock=0)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.list_url, self.add_payload(empty), format="json")

        self.assertEqual(response.status_code, 400)

    def test_missing_variant_returns_400(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.list_url, {"quantity": 1}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_unknown_variant_returns_400(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.list_url, {"variant": str(uuid.uuid4()), "quantity": 1}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_zero_quantity_returns_400(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.list_url, self.add_payload(quantity=0), format="json")
        self.assertEqual(response.status_code, 400)

    def test_negative_quantity_returns_400(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.list_url, self.add_payload(quantity=-1), format="json")
        self.assertEqual(response.status_code, 400)


class TestCartDetailAPI(CartTestBase):
    def setUp(self):
        super().setUp()
        self.item = CartItem.objects.create(
            cart=Cart.objects.create(user=self.user), variant=self.variant, quantity=2
        )
        self.their_item = CartItem.objects.create(
            cart=Cart.objects.create(user=self.other), variant=self.variant, quantity=1
        )
        self.client.force_authenticate(user=self.user)

    # ---------- retrieve ----------

    def test_retrieve_own_item(self):
        response = self.client.get(self.detail_url(self.item))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["quantity"], 2)
        self.assertEqual(response.data["subtotal"], Decimal("1100.00"))

    def test_unknown_item_returns_404(self):
        url = reverse("cart-item-detail", kwargs={"public_id": uuid.uuid4()})
        self.assertEqual(self.client.get(url).status_code, 404)

    # ---------- ownership ----------

    def test_cannot_read_another_users_item(self):
        self.assertEqual(self.client.get(self.detail_url(self.their_item)).status_code, 404)

    def test_cannot_update_another_users_item(self):
        response = self.client.put(self.detail_url(self.their_item), {"quantity": 4}, format="json")

        self.their_item.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.their_item.quantity, 1)

    def test_cannot_delete_another_users_item(self):
        response = self.client.delete(self.detail_url(self.their_item))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(CartItem.objects.filter(pk=self.their_item.pk).exists())

    def test_guest_cannot_touch_a_guest_cart_that_is_not_theirs(self):
        guest_a, guest_b = APIClient(), APIClient()
        created = guest_a.post(self.list_url, self.add_payload(), format="json")
        url = reverse("cart-item-detail", kwargs={"public_id": created.data["id"]})

        guest_b.get(self.list_url)  # gives guest B a session of their own

        self.assertEqual(guest_b.get(url).status_code, 404)
        self.assertEqual(guest_a.get(url).status_code, 200)

    def test_guest_without_session_cannot_touch_a_logged_in_users_item(self):
        guest = APIClient()  # never made a request, so no session
        url = self.detail_url(self.item)

        self.assertEqual(guest.get(url).status_code, 404)
        self.assertEqual(guest.put(url, {"quantity": 4}, format="json").status_code, 404)
        self.assertEqual(guest.delete(url).status_code, 404)
        self.assertTrue(CartItem.objects.filter(pk=self.item.pk).exists())

    # ---------- update ----------

    def test_update_quantity(self):
        response = self.client.put(self.detail_url(self.item), {"quantity": 4}, format="json")

        self.item.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Cart item updated successfully.")
        self.assertEqual(self.item.quantity, 4)

    def test_patch_also_updates_quantity(self):
        response = self.client.patch(self.detail_url(self.item), {"quantity": 3}, format="json")

        self.item.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.item.quantity, 3)

    def test_update_to_exactly_stock_is_allowed(self):
        response = self.client.put(self.detail_url(self.item), {"quantity": 5}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_update_beyond_stock_returns_400(self):
        response = self.client.put(self.detail_url(self.item), {"quantity": 6}, format="json")

        self.item.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.item.quantity, 2)

    def test_update_zero_quantity_returns_400(self):
        response = self.client.put(self.detail_url(self.item), {"quantity": 0}, format="json")

        self.item.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.item.quantity, 2)

    def test_update_missing_quantity_returns_400(self):
        response = self.client.put(self.detail_url(self.item), {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_update_cannot_change_variant(self):
        other_variant = make_variant(make_product("other-ring"))

        self.client.put(
            self.detail_url(self.item),
            {"quantity": 3, "variant": str(other_variant.public_id)},
            format="json",
        )

        self.item.refresh_from_db()
        self.assertEqual(self.item.variant_id, self.variant.public_id)

    # ---------- delete ----------

    def test_delete_item(self):
        response = self.client.delete(self.detail_url(self.item))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Cart item deleted successfully.")
        self.assertFalse(CartItem.objects.filter(pk=self.item.pk).exists())

    def test_delete_keeps_other_items(self):
        self.client.delete(self.detail_url(self.item))
        self.assertTrue(CartItem.objects.filter(pk=self.their_item.pk).exists())

    def test_requests_for_deleted_item_return_404(self):
        self.client.delete(self.detail_url(self.item))
        self.assertEqual(self.client.get(self.detail_url(self.item)).status_code, 404)