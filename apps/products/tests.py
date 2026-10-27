from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from rest_framework.test import APITestCase

from unittest.mock import patch, MagicMock
from redis.exceptions import ConnectionError as RedisConnectionError

from apps.products.models import Category, Product
from apps.products import cache_utils

User = get_user_model()


IMAGE_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04"
    b"\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)

class TestCategoryAPI(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="rings",
            slug="rings",
            description="premium rings for men and women",
            alt_text="Ring image",
            image=SimpleUploadedFile(
                "ring.gif", IMAGE_BYTES, content_type="image/gif"
            ),
        )
        self.category1 = Category.objects.create(
            name="earrings",
            slug="earrings",
            description="premium earring for men and women",
            alt_text="Earring image",
            image=SimpleUploadedFile(
                "earring.gif", IMAGE_BYTES, content_type="image/gif"
            ),
        )
        self.product = Product.objects.create(
            category=self.category,
            name="gold plated ring",
            slug="gold-plated-ring",
            description="gold plated ring for female",
            price=499.00,
            gender="female",
            is_available=True,
            is_featured=True,
        )
        self.category_url = reverse("category-list") 
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="pass1234",
            is_staff=True,
        )
        self.normal_user = User.objects.create_user(
            email="user@test.com",
            password="pass1234",
        )
        self.category_detail_url = reverse("category-detail", kwargs={"slug": self.category.slug})
        self.category_detail_url_1 = reverse("category-detail", kwargs={"slug": self.category1.slug})


    # A tiny valid image, so the image field accepts it

    def category_data(self, **changes):
        """All mandatory fields. Pass changes to override a field."""
        data = {
            "name": "Watches",
            "slug": "watches",
            "description": "premium watches for men and women",
            "alt_text": "Watches image",
            "image": SimpleUploadedFile(
                "watch.gif", IMAGE_BYTES, content_type="image/gif"
            ),
        }
        data.update(changes)
        return data
    
    # ---------- category detail ----------

    def test_category_detail_returns_200(self):
        response = self.client.get(self.category_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], self.category.name)

    def test_category_detail_not_found_returns_404(self):
        response = self.client.get(f"{self.category_url}wrong-slug/")
        self.assertEqual(response.status_code, 404)

    # ---------- category create ----------

    def test_category_create_without_login_fails(self):
        response = self.client.post(
            self.category_url, self.category_data(), format="multipart"
        )
        self.assertIn(response.status_code, (401, 403))

    def test_category_create_normal_user_returns_403(self):
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.post(
            self.category_url, self.category_data(), format="multipart"
        )
        self.assertEqual(response.status_code, 403)

    def test_category_create_admin_returns_201(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            self.category_url, self.category_data(), format="multipart"
        ) 
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Category.objects.filter(slug="watches").exists())

    def test_category_create_without_name_returns_400(self):
        self.client.force_authenticate(user=self.admin_user)
        data = self.category_data()
        data.pop("name")
        response = self.client.post(self.category_url, data, format="multipart")
        self.assertEqual(response.status_code, 400)

    def test_category_create_without_image_returns_400(self):
        self.client.force_authenticate(user=self.admin_user)
        data = self.category_data()
        data.pop("image")
        response = self.client.post(self.category_url, data, format="multipart")
        self.assertEqual(response.status_code, 400)

    def test_category_create_without_alt_text_returns_400(self):
        self.client.force_authenticate(user=self.admin_user)
        data = self.category_data()
        data.pop("alt_text")
        response = self.client.post(self.category_url, data, format="multipart")
        self.assertEqual(response.status_code, 400)

    # ---------- category delete ----------

    def test_category_delete_with_products_returns_409(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(self.category_detail_url)
        self.assertEqual(response.status_code, 409)
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_category_delete_empty_returns_204(self):

        self.client.force_authenticate(user=self.admin_user) 
        
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(self.category_detail_url_1)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Category.objects.filter(pk=self.category1.pk).exists())


class TestProductAPI(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="rings",
            slug="rings",
            description="premium rings for men and women",
            alt_text="Ring image",
            image=SimpleUploadedFile(
                "ring.gif", IMAGE_BYTES, content_type="image/gif"
            ),
        )
        self.category1 = Category.objects.create(
            name="earrings",
            slug="earrings",
            description="premium earring for men and women",
            alt_text="Earring image",
            image=SimpleUploadedFile(
                "earring.gif", IMAGE_BYTES, content_type="image/gif"
            ),
        )
        self.product = Product.objects.create(
            category=self.category,
            name="gold plated ring",
            slug="gold-plated-ring",
            description="gold plated ring for female",
            price=499.00,
            gender="female",
            is_available=True,
            is_featured=True,
        )
        self.product1 = Product.objects.create(
            category=self.category,
            name="gold plated ring",
            slug="gold-plated-male-ring",
            description="gold plated ring for male",
            price=599,
            gender="male",
            is_available=False,
            is_featured=True,
        )

        self.category_url = reverse("category-list") 
        self.list_url = reverse("product-list")
        self.detail_url = reverse("product-detail", kwargs={"slug": self.product.slug})
        self.detail_url_1 = reverse(
            "product-detail", kwargs={"slug": self.product1.slug}
        )
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="pass1234",
            is_staff=True,
        )
        self.normal_user = User.objects.create_user(
            email="user@test.com",
            password="pass1234",
        )
        self.category_detail_url = reverse("category-detail", kwargs={"slug": self.category.slug})
        self.category_detail_url_1 = reverse("category-detail", kwargs={"slug": self.category1.slug})


    # A tiny valid image, so the image field accepts it

    def category_data(self, **changes):
        """All mandatory fields. Pass changes to override a field."""
        data = {
            "name": "Watches",
            "slug": "watches",
            "description": "premium watches for men and women",
            "alt_text": "Watches image",
            "image": SimpleUploadedFile(
                "watch.gif", IMAGE_BYTES, content_type="image/gif"
            ),
        }
        data.update(changes)
        return data

    # ---------- product list ----------

    def test_product_list_return_200(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["price"], "499.00")

    def test_product_list_search_by_name(self):
        response = self.client.get(self.list_url, {"search": "ring"})
        self.assertEqual(response.data["count"], 1)

    def test_product_list_filter_by_gender(self):
        response = self.client.get(self.list_url, {"gender": "female"})
        self.assertEqual(response.data["count"], 1)

    def test_unavailable_products_are_excluded_from_filter(self):
        response = self.client.get(self.list_url, {"gender": "male"})
        self.assertEqual(response.data["count"], 0)

    # ---------- product details ----------

    def test_product_detail_return_200(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(float(response.data["price"]), self.product.price)

        response = self.client.get(self.detail_url_1) 
        self.assertEqual(response.status_code, 200)
        self.assertEqual(float(response.data["price"]), self.product1.price)

    def test_product_detail_return_404(self):
        url = reverse("product-detail", kwargs={"slug":"does-not-exist"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


def broken_cache():
    fake = MagicMock()
    fake.get.side_effect = RedisConnectionError("Redis is down")
    fake.set.side_effect = RedisConnectionError("Redis is down")
    fake.delete.side_effect = RedisConnectionError("Redis is down")
    return fake


@override_settings(CACHES=TEST_CACHES)
class TestProductCache(APITestCase):
    def setUp(self):
        cache.clear()
        self.category = Category.objects.create(name="Rings", slug="rings")
        self.product = Product.objects.create(
            category=self.category,
            name="Gold Plated Ring",
            slug="gold-plated-ring",
            description="Gold plated ring for female",
            price=499.00,
            gender="female",
            is_available=True,
        )
        self.detail_url = reverse("product-detail", kwargs={"slug": self.product.slug})
        self.list_url = reverse("product-list")

    def get_expecting_queries(self, url, queries=0):
        with self.assertNumQueries(queries):
            return self.client.get(url)

    # ---------- detail ----------

    def test_detail_second_request_uses_cache(self):
        self.client.get(self.detail_url)

        response = self.get_expecting_queries(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(float(response.data["price"]), 499.00)

    def test_detail_cache_cleared_when_product_changes(self):
        self.client.get(self.detail_url)

        with self.captureOnCommitCallbacks(execute=True):
            self.product.price = 120.00
            self.product.save()

        response = self.get_expecting_queries(self.detail_url, 3)
        self.assertEqual(float(response.data["price"]), 120.00)

        response = self.get_expecting_queries(self.detail_url, 0)
        self.assertEqual(float(response.data["price"]), 120.00)

    def test_detail_cache_cleared_when_category_changes(self):
        self.client.get(self.detail_url)

        with self.captureOnCommitCallbacks(execute=True):
            self.category.name = "Ring"
            self.category.save()

        response = self.get_expecting_queries(self.detail_url, 3)
        self.assertEqual(response.data["category"]["name"], "Ring")

        response = self.get_expecting_queries(self.detail_url)
        self.assertEqual(response.data["category"]["name"], "Ring")

    def test_detail_cache_cleared_when_product_deleted(self):
        self.client.get(self.detail_url)              

        with self.captureOnCommitCallbacks(execute=True):
            self.product.delete()

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 404)

    def test_missing_product_returns_404_and_is_not_cached(self):
        url = reverse("product-detail", kwargs={"slug": "does-not-exist"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertIsNone(cache.get(cache_utils.detail_cache_key("does-not-exist")))

    # ---------- list ----------

    def test_list_second_request_uses_cache(self):
        self.client.get(self.list_url)

        response = self.get_expecting_queries(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(float(response.data["results"][0]["price"]), 499.00)

    def test_list_refreshes_after_product_change(self):
        self.client.get(self.list_url)

        with self.captureOnCommitCallbacks(execute=True):
            self.product.price = 199.00
            self.product.save()

        response = self.get_expecting_queries(self.list_url, 4)
        self.assertEqual(float(response.data["results"][0]["price"]), 199.00)

        response = self.get_expecting_queries(self.list_url)
        self.assertEqual(float(response.data["results"][0]["price"]), 199.00)

    def test_version_changes_after_bump(self):
        old = cache_utils.get_list_version()
        cache_utils.bump_list_version()
        self.assertNotEqual(old, cache_utils.get_list_version())

    def test_same_filters_in_different_order_share_one_key(self):
        a = self.client.get(self.list_url + "?search=gold&page=1")
        b = self.client.get(self.list_url + "?page=1&search=gold")

        self.assertEqual(a.data, b.data)
        self.assertEqual(a.data["count"], 1)

        self.get_expecting_queries(self.list_url + "?page=1&search=gold", 0)

    # ---------- redis failure ----------

    def test_detail_works_when_redis_is_down(self):
        with patch.object(cache_utils, "cache", broken_cache()):
            response = self.get_expecting_queries(self.detail_url, 3)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["slug"], "gold-plated-ring")

    def test_list_works_when_redis_is_down(self):
        with patch.object(cache_utils, "cache", broken_cache()):
            response = self.get_expecting_queries(self.list_url, 4)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_admin_save_works_when_redis_is_down(self):
        with patch.object(cache_utils, "cache", broken_cache()):
            with self.captureOnCommitCallbacks(execute=True):
                self.product.price = 999
                self.product.save()

        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 999)

    def test_failure_is_logged(self):
        with patch.object(cache_utils, "cache", broken_cache()):
            with self.assertLogs("apps.products.cache_utils", level="WARNING"):
                self.client.get(self.detail_url)
