from core.events.base import BaseEvent


class OrderCreatedEvent(BaseEvent):
    """
    Event emitted when an order is successfully created.
    Payload: order_id
    Handlers: inventory (stock reduction), CRM (customer metrics), marketing (tracking)
    """
    pass


class ProductViewedEvent(BaseEvent):
    """
    Event emitted when a product page is viewed.
    Payload: product_id, user_id, session_key
    Handlers: marketing (view tracking), analytics (funnel)
    """
    pass


class StockLowEvent(BaseEvent):
    """
    Event emitted when a product's stock drops below its low_stock_threshold.
    Payload: product_id, vendor_id, current_stock
    Handlers: inventory (alert logging)
    """
    pass


class OrderStatusChangedEvent(BaseEvent):
    """
    Event emitted when an order status transitions.
    Payload: order_id, old_status, new_status
    Handlers: (future) notification system, analytics
    """
    pass
