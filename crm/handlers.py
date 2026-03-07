import logging
from core.events.dispatcher import register
from core.events.events import OrderCreatedEvent

logger = logging.getLogger(__name__)


def handle_order_created(event: OrderCreatedEvent):
    """
    Handles OrderCreatedEvent to update CRM customer metrics.
    Delegates all logic to CustomerService — no business logic here.
    """
    order_id = event.payload.get('order_id')
    if not order_id:
        logger.error("CRM received OrderCreatedEvent without order_id")
        return

    logger.info(f"[CRM] Received OrderCreatedEvent for Order {order_id}")

    from crm.services.customer_service import CustomerService
    CustomerService.update_customer_metrics(order_id)


def register_handlers():
    """Register all CRM event handlers."""
    register(OrderCreatedEvent, handle_order_created)
    logger.info("CRM event handlers registered.")
