from orders.models import Cart, CartItem

def get_user_cart(user):
    """
    Selector for fetching a user's cart with optimized queries.
    """
    return Cart.objects.filter(user=user).prefetch_related(
        'items__product__colors',
        'items__product__category',
        'items__product__subcategory',
    )

def get_user_cart_items(user):
    """
    Selector for fetching cart items.
    """
    return CartItem.objects.filter(cart__user=user).select_related('product')
