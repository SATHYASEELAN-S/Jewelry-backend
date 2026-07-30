from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="carts",
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(user__isnull=False),
                name="one_cart_per_user",
            ),
        ]

    def __str__(self):
        return f"Cart({self.user or self.session_key})"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())

from uuid import uuid4
class CartItem(models.Model):
    public_id=models.UUIDField(default=uuid4,editable=False,unique=True)    
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        "products.ProductVariant",
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "variant"], name="unique_cart_variant"
            )
        ]

    def __str__(self):
        return f"{self.quantity} x {self.variant} in cart {self.cart_id}"

    @property
    def unit_price(self):
        return self.variant.product.price + self.variant.extra_price

    @property
    def subtotal(self):
        return self.unit_price * self.quantity
