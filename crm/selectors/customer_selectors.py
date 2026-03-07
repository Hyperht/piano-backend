"""
CRM Selectors — Read-only, optimized queries for customer intelligence.
All heavy queries live here. No writes, no side effects.
"""
from typing import Optional, List, Dict, Any
from django.db.models import Sum, Count, F, Max, Value, CharField
from crm.models import CustomerProfile
from orders.models import Order, OrderItem


def get_top_customers(
    vendor=None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Returns top customers ranked by total_spent.
    Tries CustomerProfile first (pre-aggregated). If empty, falls back to
    live aggregation from Orders so the dashboard always shows real data.
    Supports vendor filtering via order items.
    """
    qs = CustomerProfile.objects.select_related('user').order_by('-total_spent')

    if vendor:
        user_ids = OrderItem.objects.filter(
            vendor=vendor
        ).values_list('order__user_id', flat=True).distinct()
        qs = qs.filter(user_id__in=user_ids)

    if qs.exists():
        return list(
            qs[:limit].values(
                'user_id',
                'user__email',
                'user__first_name',
                'user__last_name',
                'user__username',
                'total_spent',
                'orders_count',
                'last_order_date',
                'region_snapshot',
            )
        )

    # Fallback: live aggregation from Order table (always accurate)
    order_qs = Order.objects.filter(status='DELIVERED').select_related('user')
    if vendor:
        order_qs = order_qs.filter(items__vendor=vendor).distinct()

    return list(
        order_qs
        .values(
            'user__id',
            'user__email',
            'user__first_name',
            'user__last_name',
            'user__username',
        )
        .annotate(
            total_spent=Sum('total_amount'),
            orders_count=Count('id'),
        )
        .order_by('-total_spent')[:limit]
    )


def get_all_customers_with_stats(start_date=None, end_date=None):
    queryset = Order.objects.filter(status="DELIVERED")

    if start_date and end_date:
        queryset = queryset.filter(created_at__range=[start_date, end_date])

    return (
        queryset
        .values(
            "user__id",
            "user__first_name",
            "user__last_name",
            "user__email",
            "user__phone_number",
        )
        .annotate(
            total_spent=Sum("total_amount"),
            total_orders=Count("id", distinct=True),
            last_order=Max("created_at"),
            user__phone1=F("user__phone_number"),
            user__phone2=Value("", output_field=CharField()),
            user__city=Value("", output_field=CharField()),
            user__address=Value("", output_field=CharField())
        )
        .order_by("-total_spent")
    )


def get_geographic_sales(vendor=None) -> List[Dict[str, Any]]:
    """
    Sales grouped by region using Order.region_snapshot.
    No dynamic user profile joins — uses snapshot data only.
    """
    qs = Order.objects.exclude(
        region_snapshot__isnull=True
    ).exclude(
        region_snapshot=''
    ).filter(
        status__in=['DELIVERED', 'CONFIRMED', 'SHIPPED']
    )

    if vendor:
        qs = qs.filter(items__vendor=vendor).distinct()

    return list(
        qs.values('region_snapshot').annotate(
            total_revenue=Sum('total_amount'),
            total_orders=Count('id', distinct=True),
        ).order_by('-total_revenue')
    )


def get_customer_detail(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Returns detailed customer profile with order history summary.
    """
    try:
        profile = CustomerProfile.objects.select_related('user').get(user_id=user_id)
    except CustomerProfile.DoesNotExist:
        return None

    return {
        'user_id': profile.user_id,
        'username': profile.user.username,
        'email': profile.user.email,
        'first_name': profile.user.first_name,
        'last_name': profile.user.last_name,
        'total_spent': profile.total_spent,
        'orders_count': profile.orders_count,
        'last_order_date': profile.last_order_date,
        'region_snapshot': profile.region_snapshot,
        'lifetime_value': profile.lifetime_value,
        'loyalty_score': profile.loyalty_score,
        'member_since': profile.created_at,
    }


def get_customer_count_by_region() -> List[Dict[str, Any]]:
    """
    Returns customer count per region.
    Uses the pre-aggregated region_snapshot field.
    """
    return list(
        CustomerProfile.objects.exclude(
            region_snapshot__isnull=True
        ).exclude(
            region_snapshot=''
        ).values('region_snapshot').annotate(
            customer_count=Count('id'),
            total_revenue=Sum('total_spent'),
        ).order_by('-total_revenue')
    )
