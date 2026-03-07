from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from analytics.selectors.aggregations import (
    get_revenue_metrics,
    get_orders_metrics,
    get_sales_by_category,
    get_sales_by_region,
    get_top_products,
    get_funnel_counts
)
from analytics.selectors.sales import get_low_stock_products, get_recent_orders, get_most_watched, get_most_wishlisted, get_revenue_metrics as get_sales_revenue_metrics
from orders.models import Order
from tracking.models import ProductViewEvent, WishlistEvent
from products.models import Product
from users.models import CustomUser
from django.db.models import Count
from django.utils import timezone

# Orchestrates analytics domain by composing selectors into dashboard summaries, breakdowns, and gap analysis
class AggregationService:

    @staticmethod
    def get_dashboard_summary(vendor=None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        revenue_data = get_revenue_metrics(vendor=vendor, start_date=start_date, end_date=end_date)
        orders_data = get_orders_metrics(vendor=vendor, start_date=start_date, end_date=end_date)
        funnel_data = get_funnel_counts({
            'vendor': vendor,
            'start_date': start_date,
            'end_date': end_date
        })
        
        total_users = CustomUser.objects.count()
        
        # Base queries for KPIs
        orders_qs = Order.objects.all()

        if start_date:
            orders_qs = orders_qs.filter(created_at__gte=start_date)
        if end_date:
            orders_qs = orders_qs.filter(created_at__lte=end_date)

        total_orders_count = orders_qs.count()
        
        # System status properties (all time)
        active_users = CustomUser.objects.filter(is_active=True).count()
        total_products_count = Product.objects.filter(is_active=True).count()

        active_users_30d = CustomUser.objects.filter(
            last_login__gte=timezone.now() - timedelta(days=30)
        ).count()

        # Get accurate total revenue reflecting exactly what was collected (includes shipping/discounts) for the whole system
        total_revenue_system = get_sales_revenue_metrics(vendor=vendor, start_date=start_date, end_date=end_date)
        if isinstance(total_revenue_system, dict):
            total_revenue_system = total_revenue_system.get('total', 0)
        
        return {
            'revenue_metrics': revenue_data,
            'orders_metrics': orders_data,
            'funnel_metrics': funnel_data,
            'gap_analysis': AggregationService._calculate_gap_analysis(funnel_data),
            'total_revenue': float(total_revenue_system or 0),
            'total_orders': total_orders_count,
            'total_users': total_users,
            'active_users': active_users,
            'active_users_30d': active_users_30d,
            'total_products': total_products_count,
            'recent_orders': get_recent_orders(limit=5),
            'most_watched': get_most_watched(limit=5),
            'most_wishlisted': get_most_wishlisted(limit=5),
            'low_stock': get_low_stock_products(),
            'by_category': get_sales_by_category(vendor=vendor),
            'by_region': get_sales_by_region(vendor=vendor),
        }

    @staticmethod
    def _get_trending_products(model_class, count_field_name, limit=5):
        from products.models import Product
        from django.db.models import Count
        
        trending = model_class.objects.values('product_id').annotate(count=Count('id')).order_by('-count')[:limit]
        product_ids = [t['product_id'] for t in trending]
        products = {p.id: p for p in Product.objects.filter(id__in=product_ids).prefetch_related('gallery_images')}
        
        result = []
        for t in trending:
            p = products.get(t['product_id'])
            if p:
                image_obj = p.gallery_images.filter(is_primary=True).first() or p.gallery_images.first()
                result.append({
                    'name': p.name,
                    count_field_name: t['count'],
                    'image': image_obj.image.url if image_obj and image_obj.image else None
                })
        return result

    @staticmethod
    def get_sales_breakdown(vendor=None) -> Dict[str, Any]:
        return {
            'by_category': get_sales_by_category(vendor=vendor),
            'by_region': get_sales_by_region(vendor=vendor)
        }

    @staticmethod
    def get_top_performing_products(vendor=None, limit: int = 10, category_id=None, start_date=None, end_date=None) -> Dict[str, Any]:
        return {
            'by_units': get_top_products(limit=limit, category_id=category_id, start_date=start_date, end_date=end_date, vendor=vendor)
        }
        
    @staticmethod
    def _calculate_gap_analysis(funnel: Dict[str, int]) -> Dict[str, Any]:
        views = funnel.get('views', 0)
        cart_adds = funnel.get('adds_to_cart', 0)
        checkouts = funnel.get('checkouts', 0)
        orders = funnel.get('orders', 0)
        
        view_to_cart_ratio = (cart_adds / views) if views > 0 else 0
        cart_to_checkout_ratio = (checkouts / cart_adds) if cart_adds > 0 else 0
        checkout_to_order_ratio = (orders / checkouts) if checkouts > 0 else 0
        
        warnings = []
        if view_to_cart_ratio < 0.05 and views > 100:
            warnings.append("High views but low add-to-cart rate (under 5%). Consider reviewing product pricing or descriptions.")
        
        if cart_to_checkout_ratio < 0.20 and cart_adds > 50:
            warnings.append("High cart abandonment rate. Consider reviewing the checkout flow or adding cart reminders.")
            
        if checkout_to_order_ratio < 0.50 and checkouts > 20:
            warnings.append("Significant drop-off between checkout and successful order. Check payment gateways for errors.")
            
        return {
            'ratios': {
                'view_to_cart': view_to_cart_ratio,
                'cart_to_checkout': cart_to_checkout_ratio,
                'checkout_to_order': checkout_to_order_ratio
            },
            'warnings': warnings
        }
