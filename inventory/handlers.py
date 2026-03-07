import logging
from core.events.dispatcher import register
from core.events.events import StockLowEvent, OrderCreatedEvent
from inventory.services.inventory_service import InventoryService

logger = logging.getLogger(__name__)

def handle_stock_low(event: StockLowEvent):
    """
    Handles the StockLowEvent.
    In a real system, this would trigger an email or a dashboard notification.
    """
    product_id = event.payload.get('product_id')
    current_stock = event.payload.get('current_stock')
    logger.warning(f"STOCK LOW ALERT: Product {product_id} is running low (Current stock: {current_stock})")

def handle_order_created(event: OrderCreatedEvent):
    """
    Handles OrderCreatedEvent to reduce stock.
    Payload expected: { order_id: int }
    """
    order_id = event.payload.get('order_id')
    if order_id:
        logger.info(f"Inventory system received OrderCreatedEvent for order {order_id}")
        InventoryService.reduce_stock_for_order(order_id)
    else:
        logger.error("Received OrderCreatedEvent without order_id")

def register_handlers():
    register(StockLowEvent, handle_stock_low)
    register(OrderCreatedEvent, handle_order_created)
    logger.info("Inventory event handlers registered.")
