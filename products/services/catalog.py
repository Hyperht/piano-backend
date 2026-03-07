from django.db.models import F
from products.models import Product

def increment_product_views(product_id: int) -> None:
    """
    Service for incrementing the views metric of a product.
    Using F() expression to avoid race conditions.
    """
    try:
        Product.objects.filter(pk=product_id).update(views_count=F('views_count') + 1)
    except Exception:
        pass # Ignore errors for analytics metrics in case product doesn't exist
