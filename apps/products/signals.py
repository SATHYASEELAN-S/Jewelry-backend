import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver 
from django.db import transaction
from apps.products.models import Product, ProductImage, ProductVariant, Category

from .cache_utils import detail_cache_key, safe_delete, bump_list_version

logger = logging.getLogger(__name__)

def _invalidate(slugs):
    try:
        for slug in slugs:
            safe_delete(detail_cache_key(slug))
        bump_list_version()
    except Exception:
        logger.exception("Cache invalidation failed for %s", slugs)

def _schedule(slugs): 
    transaction.on_commit(lambda : _invalidate(slugs))

@receiver([post_save,post_delete], sender=Product)
def product_changed(sender, instance, **kwargs):
    _schedule([instance.slug])

@receiver([post_save, post_delete], sender=ProductImage)
def image_changed(sender, instance, **kwargs):
    _schedule([instance.product.slug])

@receiver([post_save, post_delete], sender=ProductVariant)
def variant_changed(sender, instance, **kwargs):
    _schedule([instance.product.slug])

@receiver([post_save, post_delete], sender=Category)
def category_changed(sender, instance, **kwargs):
    slugs = list(Product.objects.filter(category=instance).values_list("slug", flat=True))
    _schedule(slugs)