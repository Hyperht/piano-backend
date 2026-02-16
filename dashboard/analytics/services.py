from dashboard.utils.analytics import (
    get_revenue_metrics, get_orders_metrics, get_status_counts, get_top_selling,
    get_recent_orders, get_most_wishlisted, get_most_watched, get_total_users,
    get_total_products, get_revenue_chart, get_orders_chart, get_low_stock_products
)
from dashboard.utils.analytics import get_top_selling # Re-importing to ensure availability

class DashboardService:
    @staticmethod
    def get_aggregated_analytics():
        return {
            "total_revenue": get_revenue_metrics(),
            "total_orders": get_orders_metrics()['last_year'], # Total is strictly requested? Prompt says "total_orders". I'll use last_year or count all.
            "total_users": get_total_users(),
            "total_products": get_total_products(),
            "orders_metrics": get_orders_metrics(),
            "orders": get_orders_metrics(),
            "status_counts": get_status_counts(),
            "recent_orders": list(get_recent_orders()),
            "top_selling": [
                {
                    "name": item['product__name'],
                    "image": item['product__image'],
                    "sales_count": item['sales_count'],
                    "revenue": item['revenue']
                } for item in get_top_selling()
            ],
            "most_watched": [
                {
                    "name": item['name'],
                    "image": item['image'],
                    "count": item['views']
                } for item in get_most_watched()
            ],
            "most_wishlisted": list(get_most_wishlisted()),
            "low_stock": list(get_low_stock_products())
        }

    @staticmethod
    def get_revenue_chart(period):
        return get_revenue_chart(period)

    @staticmethod
    def get_orders_chart(period):
        return get_orders_chart(period)

    @staticmethod
    def get_top_selling_products(category_id=None):
        from users.models import OrderItem
        from django.db.models import Sum, F
        
        queryset = OrderItem.objects.all()
        if category_id and category_id != 'All':
             # Check if it's ID (int) or Name (str)
             if isinstance(category_id, int) or (isinstance(category_id, str) and category_id.isdigit()):
                 queryset = queryset.filter(product__category__id=category_id)
             elif isinstance(category_id, str):
                 queryset = queryset.filter(product__category__name__iexact=category_id)

        top_selling = (
            queryset
            .values('product__name', 'product__image') 
            .annotate(sales_count=Sum('quantity'), revenue=Sum(F('quantity') * F('price_at_purchase')))
            .order_by('-sales_count')[:5]
        )

        return [
            {
                "name": item['product__name'],
                "image": item['product__image'],
                "sales_count": item['sales_count'],
                "revenue": item['revenue']
            } for item in top_selling
        ]
