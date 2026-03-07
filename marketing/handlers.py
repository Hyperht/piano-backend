from core.events import dispatcher
from core.events.events import OrderCreatedEvent, ProductViewedEvent
import logging

logger = logging.getLogger(__name__)

def handle_order_created(event: OrderCreatedEvent):
    """
    Subscribes to OrderCreatedEvent to handle marketing/promotional logic.
    For instance: granting loyalty points, referring programs, tracing conversions.
    """
    order_id = event.payload.get('order_id')
    logger.info(f"[Marketing] Received OrderCreatedEvent for Order {order_id}")
    # Future: implement marketing side-effects (e.g. sending promotional emails)


def handle_product_viewed(event: ProductViewedEvent):
    """
    Subscribes to ProductViewedEvent to track viewing histories and recommendations.
    """
    product_id = event.payload.get('product_id')
    logger.info(f"[Marketing] Received ProductViewedEvent for Product {product_id}")
    # Future: push viewing signals for personalized promo grids


def register_handlers():
    """Register all marketing event handlers."""
    dispatcher.register(OrderCreatedEvent, handle_order_created)
    dispatcher.register(ProductViewedEvent, handle_product_viewed)
