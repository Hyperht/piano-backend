from orders.models import Cart, CartItem
from products.models import Product
from tracking.services.tracking_service import TrackingService
import logging

logger = logging.getLogger(__name__)

class CartService:
    @staticmethod
    def add_item_to_cart(user, product_id, quantity, request=None):
        cart, _ = Cart.objects.get_or_create(user=user)
        try:
            product = Product.objects.get(pk=product_id, is_active=True)
        except Product.DoesNotExist:
            raise ValueError("Product not found or inactive.")

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        if request:
            try:
                TrackingService.track_add_to_cart(request, product)
            except Exception as te:
                logger.warning(f"AddToCart tracking failed for product {product_id}: {te}")

        return cart
