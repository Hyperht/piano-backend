from orders.models import Order
from django.db.models import F, Value, CharField
from django.db.models.functions import Concat

def get_user_orders_list(user):
    """
    Selector for fetching a user's list of past orders.
    """
    return Order.objects.filter(user=user).order_by('-created_at')

def get_user_order_detail(user):
    """
    Selector for fetching a detailed single order.
    """
    return Order.objects.filter(user=user).select_related(
        'shipping_address__area__governorate'
    ).prefetch_related(
        'items__product'
    ).order_by('-created_at')

def get_all_orders_for_export(start_date=None, end_date=None):
    """
    Selector for fetching orders for analytics export.
    Returns optimized queryset for Excel generation.
    """
    qs = Order.objects.select_related(
        'user', 
        'shipping_address'
    ).prefetch_related(
        'items__vendor'
    ).order_by('-created_at')
    
    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)
        
    return qs

def get_recent_orders(limit=5, start_date=None, end_date=None):
    """
    Provides optimized read-only dashboard overview of recent orders.
    """
    queryset = Order.objects.select_related("user")

    if start_date and end_date:
        queryset = queryset.filter(created_at__range=[start_date, end_date])

    return queryset.order_by("-created_at")[:limit]

def get_all_orders_with_customer(start_date=None, end_date=None):
    """
    Returns full CRM dataset for all orders (See All).
    """
    queryset = Order.objects.select_related(
        "user", 
        "shipping_address", 
        "shipping_address__area", 
        "shipping_address__area__governorate"
    )

    if start_date and end_date:
        queryset = queryset.filter(created_at__range=[start_date, end_date])

    return (
        queryset
        .values(
            "id",
            "status",
            "total_amount",
            "cart_subtotal",
            "created_at",
            "user__id",
            "user__email",
            full_name=Concat("user__first_name", Value(" "), "user__last_name", output_field=CharField()),
            phone1=F("shipping_address__phone_number_1"),
            phone2=F("shipping_address__phone_number_2"),
            city=F("shipping_address__area__name"),
            street_address=F("shipping_address__street_address"),
            area=F("shipping_address__area__name"),
            government=F("shipping_address__area__governorate__name"),
        )
        .order_by("-created_at")
    )
