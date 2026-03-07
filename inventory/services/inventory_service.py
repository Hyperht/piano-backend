from django.db import transaction
from products.models import Product
from inventory.models import StockMovement
from core.events.dispatcher import emit
from core.events.events import StockLowEvent
import logging

logger = logging.getLogger(__name__)


class InventoryService:

    @staticmethod
    @transaction.atomic
    def reduce_stock(product: Product, quantity_to_reduce: int, reason: str = 'ORDER'):
        """
        Reduces stock for a product, creates a StockMovement record,
        and emits a StockLowEvent if the quantity falls below the threshold.
        """
        if quantity_to_reduce <= 0:
            raise ValueError("Quantity to reduce must be positive.")

        # Ensure we lock the row to avoid race conditions during concurrent orders
        product = Product.objects.select_for_update().get(pk=product.pk)

        if product.quantity < quantity_to_reduce:
            raise ValueError(f"Insufficient stock for product {product.name}. Required: {quantity_to_reduce}, Available: {product.quantity}")

        # Update and save the stock
        product.quantity -= quantity_to_reduce
        product.save()

        # Record the movement
        StockMovement.objects.create(
            product=product,
            change_amount=-quantity_to_reduce,
            reason=reason
        )

        # Check and emit StockLowEvent
        if product.quantity <= product.low_stock_threshold:
            vendor_id = product.vendor.id if getattr(product, 'vendor', None) else None
            emit(StockLowEvent(
                product_id=product.id,
                vendor_id=vendor_id,
                current_stock=product.quantity
            ))
            logger.info(f"Emitted StockLowEvent for Product ID {product.id}. Current Stock: {product.quantity}")

        return product

    @staticmethod
    @transaction.atomic
    def reduce_stock_for_order(order_id: int):
        from orders.models import OrderItem
        
        items = OrderItem.objects.filter(order_id=order_id).select_related('product')
        for item in items:
            if item.product:
                InventoryService.reduce_stock(
                    product=item.product, 
                    quantity_to_reduce=item.quantity, 
                    reason='ORDER'
                )
