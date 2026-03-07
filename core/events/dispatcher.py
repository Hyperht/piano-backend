import logging

logger = logging.getLogger(__name__)

_event_registry = {}

def register(event_type, handler):
    """Register a handler function for a specific event type."""
    _event_registry.setdefault(event_type, []).append(handler)

def emit(event):
    """Emit an event to all registered handlers synchronously.
    Matches the exact instance type to the registered handlers.
    """
    handlers = _event_registry.get(type(event), [])
    for handler in handlers:
        try:
            handler(event)
        except Exception as e:
            logger.error(f"Error executing event handler {handler.__name__} for {type(event).__name__}: {e}")
