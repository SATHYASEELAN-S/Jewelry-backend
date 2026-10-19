from rest_framework.test import APITestCase
from django.urls import reverse
from redis.exceptions import ConnectionError as RedisConnectionError
from django.core.cache import cache
from django.test import override_settings
from unittest.mock import patch, MagicMock

from apps.products.models import Category, Product

from apps.products import cache_utils


class TestProductAPI(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="rings", slug="rings")
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

    def test_product_list_return_200(self):
        url = reverse("product-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["price"], "499.00")

    def test_product_list_search_by_name(self):
        url = reverse("product-list")
        response = self.client.get(url, {"search": "ring"})
        self.assertEqual(response.data["count"], 1)

    def test_product_list_search_by_gender(self):
        url = reverse("product-list")
        response = self.client.get(url)
        self.assertEqual(response.data["count"], 1)

    def test_product_list_search_by_gender_returns_empty(self):
        url = reverse("product-list")
        response = self.client.get(url, {"gender": "male", "is_available": "true"})
        self.assertEqual(response.data["count"], 0)


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
