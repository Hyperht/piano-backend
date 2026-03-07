import logging
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from core.events.dispatcher import register
from core.events.events import OrderCreatedEvent, ProductViewedEvent
from analytics.models import DailySalesSummary

logger = logging.getLogger(__name__)

@transaction.atomic
def handle_order_created_analytics(event: OrderCreatedEvent):
    order_id = event.payload.get('order_id')
    if not order_id:
        return
    
    from orders.models import Order
    try:
        order = Order.objects.get(id=order_id)
        # Update daily sales summary
        date = order.created_at.date()
        summary, _ = DailySalesSummary.objects.get_or_create(date=date)
        summary.total_orders = F('total_orders') + 1
        summary.total_revenue = F('total_revenue') + order.final_total
        summary.save(update_fields=['total_orders', 'total_revenue'])
        logger.info(f"[Analytics] Updated DailySalesSummary for order {order_id}")
    except Order.DoesNotExist:
        logger.error(f"[Analytics] Order {order_id} not found")

@transaction.atomic
def handle_product_viewed_analytics(event: ProductViewedEvent):
    # Just increment today's views
    date = timezone.now().date()
    summary, _ = DailySalesSummary.objects.get_or_create(date=date)
    summary.total_views = F('total_views') + 1
    summary.save(update_fields=['total_views'])

def register_handlers():
    register(OrderCreatedEvent, handle_order_created_analytics)
    register(ProductViewedEvent, handle_product_viewed_analytics)
    logger.info("Analytics event handlers registered.")
