from analytics.selectors.sales import (
    get_revenue_metrics, get_orders_metrics, get_status_counts, get_top_selling,
    get_recent_orders, get_most_wishlisted, get_most_watched, get_total_users,
    get_total_products, get_revenue_chart, get_orders_chart, get_low_stock_products
)
from orders.models import OrderItem
from django.db.models import Sum, F


# Provides pre-aggregated dashboard metrics using read-only selectors from analytics.selectors.sales
class DashboardService:
    @staticmethod
    def get_aggregated_analytics():
        orders_metrics = get_orders_metrics()
        return {
            "total_revenue": get_revenue_metrics(),
            "total_orders": orders_metrics["last_year"],
            "total_users": get_total_users(),
            "total_products": get_total_products(),
            "orders_metrics": orders_metrics,
            "status_counts": get_status_counts(),
            "recent_orders": list(get_recent_orders()),
            "top_selling": get_top_selling(),
            "most_watched": get_most_watched(),
            "most_wishlisted": list(get_most_wishlisted()),
            "low_stock": list(get_low_stock_products()),
        }

    @staticmethod
    def get_revenue_chart(period):
        return get_revenue_chart(period)

    @staticmethod
    def get_orders_chart(period):
        return get_orders_chart(period)

    @staticmethod
    def get_top_selling_products(category_id=None):
        queryset = OrderItem.objects.all()
        if category_id and category_id != "All":
            if isinstance(category_id, int) or (isinstance(category_id, str) and category_id.isdigit()):
                queryset = queryset.filter(product__category__id=category_id)
            elif isinstance(category_id, str):
                queryset = queryset.filter(product__category__name__iexact=category_id)

        top_selling = (
            queryset
            .values("product__id", "product__name")
            .annotate(sales_count=Sum("quantity"), revenue=Sum(F("quantity") * F("price_snapshot")))
            .order_by("-sales_count")[:5]
        )

        from products.models import Product
        product_ids = [item["product__id"] for item in top_selling]
        products = {p.id: p for p in Product.objects.filter(id__in=product_ids).prefetch_related("gallery_images")}

        result = []
        for item in top_selling:
            p = products.get(item["product__id"])
            img = None
            if p:
                img = p.gallery_images.filter(is_primary=True).first() or p.gallery_images.first()
            result.append({
                "name": item["product__name"],
                "image": img.image.url if img and img.image else None,
                "sales_count": item["sales_count"],
                "revenue": item["revenue"],
            })
        return result
