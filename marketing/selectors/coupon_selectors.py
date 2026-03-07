"""
Marketing Selectors — Read-only analytics queries for coupons and campaigns.
All heavy aggregation queries live here. No writes.
"""
from typing import Optional, List, Dict, Any
from decimal import Decimal
from django.db.models import Sum, Count, Avg, F, Q, Case, When, DecimalField
from django.db.models.functions import Coalesce

from marketing.models import Coupon, CouponUsage
from orders.models import Order


def get_coupon_analytics() -> Dict[str, Any]:
    """
    Returns overall coupon analytics:
    - Total usage count
    - Total revenue impact (discount given)
    - Top performing coupons
    - Conversion rate (orders with coupons vs total)
    """
    total_usage = CouponUsage.objects.count()
    total_discount_given = CouponUsage.objects.aggregate(
        total=Coalesce(Sum('discount_applied'), Decimal('0.00'))
    )['total']

    total_orders = Order.objects.count()
    orders_with_coupon = Order.objects.filter(
        coupon_usages__isnull=False
    ).distinct().count()

    conversion_rate = (orders_with_coupon / total_orders) if total_orders > 0 else 0

    return {
        'total_usage': total_usage,
        'total_discount_given': total_discount_given,
        'orders_with_coupon': orders_with_coupon,
        'total_orders': total_orders,
        'conversion_rate': round(conversion_rate, 4),
    }


def get_top_performing_coupons(
    vendor=None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Returns top performing coupons ranked by usage count and revenue impact.
    """
    qs = Coupon.objects.annotate(
        usage_count=Count('usages'),
        total_discount=Coalesce(Sum('usages__discount_applied'), Decimal('0.00')),
        total_order_revenue=Coalesce(
            Sum('usages__order__total_amount'),
            Decimal('0.00')
        ),
    )

    if vendor:
        qs = qs.filter(vendor=vendor)

    return list(
        qs.order_by('-usage_count')[:limit].values(
            'id', 'code', 'discount_type', 'discount_value',
            'usage_count', 'total_discount', 'total_order_revenue',
            'max_uses', 'used_count', 'is_active',
        )
    )


def get_campaign_performance(vendor=None) -> Dict[str, Any]:
    """
    Campaign-level performance metrics:
    - Campaign revenue (orders using coupon)
    - Revenue lift vs non-coupon orders
    - Orders per coupon
    - Vendor filter support
    """
    # Orders WITH coupons
    coupon_orders_qs = Order.objects.filter(
        coupon_usages__isnull=False,
        status__in=['DELIVERED', 'CONFIRMED', 'SHIPPED']
    ).distinct()

    # Orders WITHOUT coupons
    non_coupon_orders_qs = Order.objects.filter(
        coupon_usages__isnull=True,
        status__in=['DELIVERED', 'CONFIRMED', 'SHIPPED']
    )

    if vendor:
        coupon_orders_qs = coupon_orders_qs.filter(items__vendor=vendor).distinct()
        non_coupon_orders_qs = non_coupon_orders_qs.filter(items__vendor=vendor).distinct()

    coupon_stats = coupon_orders_qs.aggregate(
        revenue=Coalesce(Sum('total_amount'), Decimal('0.00')),
        count=Count('id', distinct=True),
        avg_order_value=Coalesce(Avg('total_amount'), Decimal('0.00')),
    )

    non_coupon_stats = non_coupon_orders_qs.aggregate(
        revenue=Coalesce(Sum('total_amount'), Decimal('0.00')),
        count=Count('id', distinct=True),
        avg_order_value=Coalesce(Avg('total_amount'), Decimal('0.00')),
    )

    # Revenue lift calculation
    coupon_avg = coupon_stats['avg_order_value'] or Decimal('0.00')
    non_coupon_avg = non_coupon_stats['avg_order_value'] or Decimal('0.00')
    revenue_lift = (
        ((coupon_avg - non_coupon_avg) / non_coupon_avg)
        if non_coupon_avg > 0 else Decimal('0.00')
    )

    # Per-coupon breakdown
    per_coupon = list(
        CouponUsage.objects.values(
            'coupon__code', 'coupon__discount_type', 'coupon__discount_value'
        ).annotate(
            orders=Count('order', distinct=True),
            total_discount=Sum('discount_applied'),
            total_revenue=Coalesce(Sum('order__total_amount'), Decimal('0.00')),
        ).order_by('-total_revenue')[:20]
    )

    return {
        'coupon_orders': {
            'revenue': coupon_stats['revenue'],
            'count': coupon_stats['count'],
            'avg_order_value': coupon_stats['avg_order_value'],
        },
        'non_coupon_orders': {
            'revenue': non_coupon_stats['revenue'],
            'count': non_coupon_stats['count'],
            'avg_order_value': non_coupon_stats['avg_order_value'],
        },
        'revenue_lift': round(float(revenue_lift), 4),
        'per_coupon_breakdown': per_coupon,
    }

def get_top_coupons(limit=5, start_date=None, end_date=None):
    """
    Returns coupons ordered by usage/revenue. 
    Starts from Coupon model so even unused coupons appear.
    """
    qs = Coupon.objects.all()
    
    # We filter usage by date if provided
    usage_filter = Q()
    if start_date and end_date:
        usage_filter = Q(usages__created_at__range=[start_date, end_date])

    # Proper ORM grouping: values() determines GROUP BY, annotate() adds aggregation
    stats = list(
        qs.annotate(
            usage_cnt=Count("usages", filter=usage_filter),
            # Count distinct users who used the coupon
            usr_cnt=Count("usages__user", distinct=True, filter=usage_filter),
            rev_gen=Coalesce(
                Sum("usages__order__total_amount", filter=usage_filter), 
                Decimal("0.00")
            )
        )
        .values("code", "discount_value", "usage_cnt", "usr_cnt", "rev_gen", "discount_type")
        .order_by("-rev_gen", "-usage_cnt")[:limit]
    )

    # Map back to desired frontend keys if needed (optional but good for clarity)
    return [
        {
            'code': s['code'],
            'discount_value': s['discount_value'],
            'usage_count': s['usage_cnt'],
            'users_count': s['usr_cnt'],
            'revenue_generated': float(s['rev_gen']),
            'discount_type': s['discount_type']
        } for s in stats
    ]
