# cart/cart_utils.py
from .models import Cart, CartItem


def merge_guest_cart_into_user_cart(request, user):
    session_key = request.session.session_key
     
    if not session_key:
        return

    try:
        guest_cart = Cart.objects.get(session_key=session_key, user__isnull=True)
    except Cart.DoesNotExist:
        return

    user_cart, _ = Cart.objects.get_or_create(user=user) 
    
    for guest_item in guest_cart.items.all():
        existing_item = CartItem.objects.filter(
            cart=user_cart, variant=guest_item.variant
        ).first()

        if existing_item:
            existing_item.quantity += guest_item.quantity
            existing_item.save()
        else:
            guest_item.cart = user_cart
            guest_item.save()

    guest_cart.delete()