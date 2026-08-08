import logging

import razorpay
from django.conf import settings

from apps.accounts.models import Address
from apps.carts.models import CartItem
from apps.orders.models import Order, OrderItem
from apps.products.models import ProductVariant

from .models import Payment

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

logger = logging.getLogger(__name__)

REFUND_MESSAGE = {
            "refund_processing": "Refund is already being processed",
            "refunded": "Refund has already been completed",
            "refund_failed": "A previous refund attempt failed",
        }


class RefundService:
    """
    Payment-domain refund logic, independent of any webhook payload.
    Called from PaymentService (webhook flow) and from the order-cancel
    view (a completely different trigger) — neither needs to know about
    the other.
    """

    def issue_refund(self, payment, razorpay_payment_id):
        """
        Attempts a refund for a paid-but-unfulfilled payment.
        Returns an outcome dict.
        """
        try:
            refund = client.payment.refund(
                razorpay_payment_id,
                {"amount": int(payment.amount * 100), "speed": "normal"},
            )
        except razorpay.errors.BadRequestError as e:
            msg = str(e)
            if "already been refunded" in msg or "fully refunded" in msg:

                payment.set_status("refunded")

                logger.info(
                    "Payment %s already refunded on Razorpay, reconciled local state.",
                    payment.razorpay_order_id,
                )

                return {
                    "outcome": "already_handled",
                    "message": "Already refunded on Razorpay; local state reconciled",
                }

            payment.set_status("refund_failed")
            logger.error(
                "Refund failed for payment %s: %s", payment.razorpay_order_id, msg
            )

            return {"outcome": "failed", "message": f"Refund failed: {msg}"}

        payment.razorpay_refund_id = refund["id"]
        payment.save(update_fields=["razorpay_refund_id"])

        return {
            "outcome": "success",
            "message": "Your order has been cancelled, refund initiated",
        }


class PaymentService:
    """
    Business logic for Razorpay payment webhooks.
    Knows nothing about HTTP — the view is responsible for signature
    verification, extracting request.data, and translating the outcome
    dict returned by process() into an HttpResponse.
    """

    def __init__(self, payload):
        self.payload = payload
        self.event = payload.get("event")
        self.refund_service = RefundService()

    # Helper functions

    def update_payment_id(self, payment, razorpay_payment_id):
        payment.razorpay_payment_id = razorpay_payment_id
        payment.save(update_fields=["razorpay_payment_id"])

    def check_stock(self, cart_items):
        """
        Locks each variant referenced by the cart and checks stock.
        Returns (locked_variants, is_unfulfillable).
        """
        locked_variants = {}
        stock_issues = []
        missing_variant = False

        for item in cart_items:
            try:
                variant = ProductVariant.objects.select_for_update().get(
                    public_id=item.variant_id
                )
            except ProductVariant.DoesNotExist:
                missing_variant = True
                break

            locked_variants[item.id] = variant
            if variant.stock < item.quantity:
                stock_issues.append(f"{variant}: only {variant.stock} left")

        is_unfulfillable = missing_variant or bool(stock_issues)
        return locked_variants, is_unfulfillable

    def build_order(self, payment, cart_items, locked_variants, razorpay_payment_id):
        cart = payment.cart
        address = Address.objects.filter(user=payment.user, is_default=True).first()

        order = Order.objects.create(
            user=payment.user,
            shipping_street=address.street,
            shipping_city=address.city,
            shipping_state=address.state,
            shipping_pincode=address.pincode,
            shipping_landmark=address.landmark,
            total_price=cart.total_price,
        )
        order.set_status("pending")

        for item in cart_items:
            print(locked_variants[item.id])
            variant = locked_variants[item.id]
            variant.stock -= item.quantity
            variant.save(update_fields=["stock"])

            OrderItem.objects.create(
                order=order,
                variant=variant,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
            item.delete()

        payment.order = order
        self.update_payment_id(payment, razorpay_payment_id)
        payment.save(update_fields=["order"])
        payment.set_status("success")

        order.set_status("confirmed")

        return {"outcome": "success", "message": "Payment processed, order created"}

    # (called only by the dispatcher, one per event type)

    def handle_payment_failed(self, payment, razorpay_payment_id):
        self.update_payment_id(payment, razorpay_payment_id)
        payment.set_status("failed")
        return {"outcome": "failed", "message": "Payment marked as failed"}

    def handle_refund_created(self, payment):
       
        if payment.status in ("refund_processing", "refunded", "refund_failed"):
            return {
                "outcome": "already_handled",
                "message": f"{REFUND_MESSAGE[payment.status]}",
            }

        payment.set_status("refund_processing")
        return {
            "outcome": "unfulfilled",
            "message": "Refund is now processing",
        }

    def handle_refund_processed(self, payment):
        if payment.status in ("refunded", "refund_failed"):
            return {
                "outcome": "already_handled",
                "message": f"{REFUND_MESSAGE[payment.status]}",
            }
        payment.set_status("refunded")
        return {"outcome": "success", "message": "Refund processed"}

    def handle_refund_failed(self, payment):
        if payment.status in ("refund_failed"):
            return {
                "outcome": "already_handled",
                "message": f"{REFUND_MESSAGE[payment.status]}",
            }
        payment.set_status("refund_failed")
        return {"outcome": "failed", "message": "Refund failed"}

    def handle_payment_captured(self, payment, razorpay_payment_id):
        current_status = payment.status

        if current_status == "success":
            return {
                "outcome": "already_handled",
                "message": "Payment already processed",
            }

        if current_status == "paid_unfulfilled":
            return {
                "outcome": "already_handled",
                "message": "Order already marked as unfulfilled",
            }

        if current_status == "refund_processing":
            return {
                "outcome": "already_handled",
                "message": "Refund already in progress",
            }

        cart_items = CartItem.objects.filter(cart=payment.cart)
        locked_variants, is_unfulfillable = self.check_stock(cart_items)

        if is_unfulfillable:
            self.update_payment_id(payment, razorpay_payment_id)
            payment.set_status("paid_unfulfilled")
            self.refund_service.issue_refund(payment, razorpay_payment_id)
            return {
                "outcome": "unfulfilled",
                "message": "Order could not be fulfilled; refund initiated",
            }

        return self.build_order(
            payment, cart_items, locked_variants, razorpay_payment_id
        )

    # Dispatcher — the only method the view calls

    def process(self):
        payment_entity = self.payload["payload"]["payment"]["entity"]
        razorpay_order_id = payment_entity["order_id"]
        razorpay_payment_id = payment_entity["id"]

        payment = Payment.objects.filter(razorpay_order_id=razorpay_order_id).first()
        if payment is None:
            return {"outcome": "not_found", "message": "Payment not found"}

        payment = Payment.objects.select_for_update().get(pk=payment.pk)

        logger.info("Razorpay webhook event=%s order=%s", self.event, razorpay_order_id)

        if self.event == "payment.failed":
            return self.handle_payment_failed(payment, razorpay_payment_id)

        if self.event == "refund.created":
            return self.handle_refund_created(payment)

        if self.event == "refund.processed":
            return self.handle_refund_processed(payment)

        if self.event == "refund.failed":
            return self.handle_refund_failed(payment)

        if self.event == "payment.captured":
            return self.handle_payment_captured(payment, razorpay_payment_id)

        return {"outcome": "ignored", "message": "Event ignored"}
