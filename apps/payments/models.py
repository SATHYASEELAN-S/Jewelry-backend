from django.db import models
from uuid import uuid4
from django.contrib.auth import get_user_model

from apps.orders.models import Order
from apps.carts.models import Cart

User = get_user_model()


class Payment(models.Model):
    STATUS_CHOICES = [
        ("created", "Created"),
        ("success", "Success"),
        ("paid_unfulfilled", "Paid Unfulfilled"),
        ("failed", "Failed"),
        ("refund_processing", "Refund Processing"),
        ("refunded", "Refunded"),
        ("refund_failed", "Refund Failed"),
    ]

    public_id = models.UUIDField(default=uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="payments")
    cart = models.ForeignKey(Cart, on_delete=models.PROTECT, related_name="payments")
    cart_snapshot = models.JSONField(default=list, blank=True)
    order = models.ForeignKey(
        Order, on_delete=models.PROTECT, null=True, blank=True, related_name="payments"
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="created")

    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    razorpay_refund_id = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        latest_status = self.status_history.last()

        if latest_status:
            return f"{self.razorpay_order_id} - {latest_status.status}"

        return self.razorpay_order_id

    @property
    def status(self):
        latest = self.status_history.last()
        return latest.status if latest else None

    def set_status(self, new_status):
        return PaymentStatusHistory.objects.create(payment=self, status=new_status)


class PaymentStatusHistory(models.Model):
    public_id = models.UUIDField(default=uuid4, editable=False, unique=True)
    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name="status_history"
    )
    status = models.CharField(max_length=20, choices=Payment.STATUS_CHOICES)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["changed_at"]

    def __str__(self):
        return f"{self.status} -{self.payment.razorpay_order_id} "
