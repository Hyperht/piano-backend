from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone
from typing import Optional, Dict, Any, List
from datetime import datetime

from orders.models import Order, OrderItem
from tracking.models import ProductViewEvent, AddToCartEvent, CheckoutEvent, WishlistEvent
from products.models import Product

def get_revenue_metrics(vendor=None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
    qs = OrderItem.objects.select_related('order').exclude(order__status='CANCELLED')
    
    if vendor:
        qs = qs.filter(vendor=vendor)
    if start_date:
        qs = qs.filter(order__created_at__gte=start_date)
    if end_date:
        qs = qs.filter(order__created_at__lte=end_date)
        
    res = qs.aggregate(total_revenue=Sum('subtotal'))
    
    # Revenue over time (daily)
    timeline = qs.annotate(date=TruncDay('order__created_at')) \
                 .values('date') \
                 .annotate(daily_revenue=Sum('subtotal')) \
                 .order_by('date')
                 
    return {
        'total_revenue': res['total_revenue'] or 0,
        'timeline': list(timeline)
    }

def get_orders_metrics(vendor=None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
    qs = OrderItem.objects.select_related('order')
    
    if vendor:
        qs = qs.filter(vendor=vendor)
    if start_date:
        qs = qs.filter(order__created_at__gte=start_date)
    if end_date:
        qs = qs.filter(order__created_at__lte=end_date)
        
    counts = qs.aggregate(
        total_items=Sum('quantity'),
        total_orders=Count('order', distinct=True)
    )
    
    status_counts = qs.values('order__status').annotate(count=Count('order', distinct=True))
    
    return {
        'total_orders': counts['total_orders'] or 0,
        'total_items': counts['total_items'] or 0,
        'by_status': list(status_counts)
    }

def get_sales_by_category(vendor=None) -> List[Dict[str, Any]]:
    qs = OrderItem.objects.exclude(order__status='CANCELLED')
    if vendor:
        qs = qs.filter(vendor=vendor)
        
    return list(
        qs.values('product__category__name')
          .annotate(revenue=Sum('subtotal'), units_sold=Sum('quantity'))
          .order_by('-revenue')
    )

def get_sales_by_region(vendor=None) -> List[Dict[str, Any]]:
    qs = OrderItem.objects.exclude(order__status='CANCELLED').exclude(order__region_snapshot__isnull=True).exclude(order__region_snapshot='')
    if vendor:
        qs = qs.filter(vendor=vendor)
        
    return list(
        qs.values('order__region_snapshot')
          .annotate(revenue=Sum('subtotal'), total_orders=Count('order', distinct=True))
          .order_by('-revenue')
    )

def get_top_products(limit=5, category_id=None, start_date=None, end_date=None, vendor=None):
    queryset = OrderItem.objects.exclude(order__status="CANCELLED")

    if vendor:
        queryset = queryset.filter(vendor=vendor)

    if start_date and end_date:
        queryset = queryset.filter(order__created_at__range=[start_date, end_date])

    if category_id:
        queryset = queryset.filter(product__category_id=category_id)

    top_stats = list(
        queryset
        .values("product_id")
        .annotate(
            sales_count=Sum("quantity"),
            revenue=Sum("subtotal")
        )
        .order_by("-sales_count")[:limit]
    )
    
    product_ids = [item['product_id'] for item in top_stats]
    products = {
        p.id: p 
        for p in Product.objects.filter(id__in=product_ids).prefetch_related('gallery_images')
    }
    
    results = []
    for item in top_stats:
        p = products.get(item['product_id'])
        if p:
            image_obj = p.gallery_images.filter(is_primary=True).first() or p.gallery_images.first()
            results.append({
                'id': p.id,
                'name': p.name,
                'sales_count': item['sales_count'],
                'revenue': float(item['revenue']),
                'image': image_obj.image.url if image_obj and image_obj.image else None
            })
    return results
def get_funnel_counts(filters: Dict[str, Any]) -> Dict[str, int]:
    vendor = filters.get('vendor')
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    product = filters.get('product')
    traffic_source = filters.get('traffic_source')
    
    views_qs = ProductViewEvent.objects.all()
    cart_qs = AddToCartEvent.objects.all()
    checkout_qs = CheckoutEvent.objects.all()
    orders_qs = Order.objects.all()

    if start_date:
        views_qs = views_qs.filter(created_at__gte=start_date)
        cart_qs = cart_qs.filter(created_at__gte=start_date)
        checkout_qs = checkout_qs.filter(created_at__gte=start_date)
        orders_qs = orders_qs.filter(created_at__gte=start_date)
        
    if end_date:
        views_qs = views_qs.filter(created_at__lte=end_date)
        cart_qs = cart_qs.filter(created_at__lte=end_date)
        checkout_qs = checkout_qs.filter(created_at__lte=end_date)
        orders_qs = orders_qs.filter(created_at__lte=end_date)

    if traffic_source:
        views_qs = views_qs.filter(traffic_source=traffic_source)
        cart_qs = cart_qs.filter(traffic_source=traffic_source)
        checkout_qs = checkout_qs.filter(traffic_source=traffic_source)
        orders_qs = orders_qs.filter(traffic_source=traffic_source)
        
    if product:
        views_qs = views_qs.filter(product=product)
        cart_qs = cart_qs.filter(product=product)
        # Checkouts and Orders are cart/order level; filter orders by product when product is specified
        orders_qs = orders_qs.filter(items__product=product).distinct()

    if vendor:
        views_qs = views_qs.filter(vendor=vendor)
        cart_qs = cart_qs.filter(vendor=vendor)
        orders_qs = orders_qs.filter(items__vendor=vendor).distinct()

    # CheckoutEvent filtering for vendor/product is session-based and not available at the cart-item level
        
    return {
        'views': views_qs.values('session_id').distinct().count(),
        'adds_to_cart': cart_qs.values('session_id').distinct().count(),
        'checkouts': checkout_qs.values('session_id').distinct().count(),
        'orders': orders_qs.count()
    }

def get_intent_metrics(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    vendor = filters.get('vendor')
    
    wishlist_qs = WishlistEvent.objects.all()
    if vendor:
        wishlist_qs = wishlist_qs.filter(vendor=vendor)
        
    return list(
        wishlist_qs.values('product__name')
        .annotate(wishlists=Count('id'))
        .order_by('-wishlists')[:10]
    )

def get_traffic_source_breakdown(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    vendor = filters.get('vendor')
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')

    qs = Order.objects.exclude(status='CANCELLED')
    
    if start_date:
        qs = qs.filter(created_at__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__lte=end_date)
    if vendor:
        qs = qs.filter(items__vendor=vendor).distinct()

    return list(
        qs.values('traffic_source')
          .annotate(
              revenue=Sum('total_amount'),
              orders=Count('id', distinct=True)
          )
          .order_by('-revenue')
    )

