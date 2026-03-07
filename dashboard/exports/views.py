import logging
from datetime import timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from dashboard.utils.export_utils import generate_excel_report, generate_pdf_report
from analytics.selectors.sales import get_top_selling, get_recent_orders, get_revenue_metrics, get_revenue_chart
from orders.models import Order
from users.models import CustomUser
from products.models import Product
from django.db.models import Sum, Count

logger = logging.getLogger(__name__)


class ExportAnalyticsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        export_type = request.query_params.get('type', 'excel')
        period_str = request.query_params.get('period', '30')
        try:
            period = int(period_str)
        except ValueError:
            period = 30
            
        logger.info(f"Export requested: type={export_type}, period={period}, user={request.user}")

        end_date = timezone.now()
        start_date = end_date - timedelta(days=period)

        from analytics.selectors.aggregations import get_top_products
        from inventory.selectors.stock import get_stock_needed
        from marketing.selectors.coupon_selectors import get_top_coupons
        from analytics.selectors.customers import get_top_customers_summary
        
        # Build analytics dict with robust selectors
        top_selling = get_top_products(limit=10, start_date=start_date, end_date=end_date)
        recent_orders = get_recent_orders(limit=20, start_date=start_date, end_date=end_date)
        top_customers = get_top_customers_summary(limit=10, start_date=start_date, end_date=end_date)
        active_users = CustomUser.objects.filter(is_active=True).count()
        stock_needed = list(get_stock_needed(limit=10))
        top_coupons = get_top_coupons(limit=10, start_date=start_date, end_date=end_date)
        revenue_chart = get_revenue_chart(period=period)

        # Ensure total_revenue is a float for the summary
        revenue_metrics = get_revenue_metrics(start_date=start_date, end_date=end_date)
        total_revenue_val = 0.0
        if isinstance(revenue_metrics, dict):
            total_revenue_val = float(revenue_metrics.get('total_revenue', 0))
        else:
            total_revenue_val = float(revenue_metrics or 0)

        # Get filtered counts for orders
        total_orders_filtered = Order.objects.filter(created_at__range=[start_date, end_date]).count()

        analytics = {
            'period': period,
            'start_date': start_date,
            'end_date': end_date,
            'total_revenue': total_revenue_val,
            'total_orders': total_orders_filtered,
            'total_users': CustomUser.objects.count(),
            'active_users': active_users,
            'top_selling': top_selling,
            'recent_orders': recent_orders,
            'top_customers': top_customers,
            'stock_needed': stock_needed,
            'top_coupons': top_coupons,
            'revenue_chart': revenue_chart,
        }

        if export_type == 'pdf':
            return generate_pdf_report(analytics)
        else:
            return generate_excel_report(analytics)
