from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("returned", "Returned"),
    ]

    public_id = models.UUIDField(default=uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
    order_number = models.CharField(max_length=20, unique=True)
    shipping_street = models.CharField(max_length=255)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_pincode = models.CharField(max_length=6)
    shipping_landmark = models.CharField(max_length=255, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order_number} -{self.public_id} "

    def save(self, *args, **kwargs):
        if not self.order_number:
            date_part = timezone.now().strftime("%Y%m%d")
            random_part = uuid4().hex[:8].upper()
            self.order_number = f"ORD{date_part}{random_part}"
        super().save(*args, **kwargs)

    @property
    def status(self):
        latest = self.status_history.last()
        return latest.status if latest else None

    def set_status(self, new_status):
        return self.status_history.create(status=new_status)

class OrderItem(models.Model):
    public_id = models.UUIDField(default=uuid4, editable=False, unique=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        "products.ProductVariant",
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.variant.product.name}"


class OrderStatusHistory(models.Model):
    public_id = models.UUIDField(default=uuid4, editable=False, unique=True)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="status_history"
    )
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["changed_at"]

    def __str__(self):
        return f"{self.order.order_number} - {self.status}"
