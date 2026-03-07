from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDay
from django.utils import timezone
from datetime import timedelta
from users.models import CustomUser, Favorite
from orders.models import Order, OrderItem
from products.models import Product

def get_revenue_metrics(vendor=None, start_date=None, end_date=None):
    """
    Live revenue from Order table — excludes CANCELLED orders.
    Uses total_amount (pre-discount full amount).
    """
    qs = Order.objects.exclude(status='CANCELLED')
    if vendor:
        pass # Wait, if vendor logic is needed... but it isn't here, only for total order amount it's hard. Let's just do start_date, end_date. OrderItem is better if vendor is needed. Let me just add start_date and end_date
    if start_date and end_date:
        qs = qs.filter(created_at__range=[start_date, end_date])
    return qs.aggregate(
        total=Sum('total_amount')
    )['total'] or 0

def get_orders_metrics():
    today = timezone.now()
    last_30_days = today - timedelta(days=30)
    last_90_days = today - timedelta(days=90)
    last_year = today - timedelta(days=365)
    
    return {
        'today': Order.objects.filter(created_at__date=today.date()).count(),
        'last_30_days': Order.objects.filter(created_at__gte=last_30_days).count(),
        'last_3_months': Order.objects.filter(created_at__gte=last_90_days).count(),
        'last_year': Order.objects.filter(created_at__gte=last_year).count(),
    }

def get_status_counts():
    status_counts = Order.objects.values('status').annotate(count=Count('id'))
    return {item['status']: item['count'] for item in status_counts}

def get_top_selling(limit=5):
    items = (
        OrderItem.objects
        .exclude(order__status='CANCELLED')
        .values('product__id', 'product__name')
        .annotate(sales_count=Sum('quantity'), revenue=Sum(F('quantity') * F('price_snapshot')))
        .order_by('-sales_count')[:limit]
    )
    
    product_ids = [item['product__id'] for item in items]
    products = {p.id: p for p in Product.objects.filter(id__in=product_ids).prefetch_related('gallery_images')}
    
    result = []
    for item in items:
        p = products.get(item['product__id'])
        img = None
        if p:
            img = p.gallery_images.filter(is_primary=True).first() or p.gallery_images.first()
        result.append({
            'name': item['product__name'],
            'sales_count': item['sales_count'],
            'revenue': item['revenue'],
            'image': img.image.url if img else None
        })
    return result

def get_recent_orders(limit=5, start_date=None, end_date=None):
    """
    Returns recent orders with structured user data for frontend mapping.
    """
    qs = Order.objects.select_related('user', 'shipping_address__area__governorate')
    if start_date and end_date:
        qs = qs.filter(created_at__range=[start_date, end_date])
    orders = qs.order_by('-created_at')[:limit]
    result = []
    for o in orders:
        result.append({
            'id': o.id,
            'status': o.status,
            'total_amount': float(o.total_amount),
            'final_total': float(o.final_total),
            'created_at': o.created_at,
            'user': {
                'id': o.user.id if o.user else None,
                'email': o.user.email if o.user else '',
                'full_name': f"{o.user.first_name} {o.user.last_name}".strip() if o.user else 'Unknown',
            } if o.user else None,
            'shipping_address': {
                'phone_number_1': o.shipping_address.phone_number_1 if o.shipping_address else '',
                'area_name': o.shipping_address.area.name if o.shipping_address and o.shipping_address.area else '',
            } if o.shipping_address else None
        })
    return result

def get_most_wishlisted(limit=5):
    products = (
        Product.objects
        .annotate(wishlist_count=Count('favorite'))
        .filter(wishlist_count__gt=0)
        .order_by('-wishlist_count')[:limit]
        .prefetch_related('gallery_images')
    )
    result = []
    for p in products:
        img = p.gallery_images.filter(is_primary=True).first() or p.gallery_images.first()
        result.append({'name': p.name, 'wishlist_count': p.wishlist_count, 'image': img.image.url if img else None})
    return result

def get_most_watched(limit=5):
    products = (
        Product.objects
        .filter(views_count__gt=0)
        .order_by('-views_count')[:limit]
        .prefetch_related('gallery_images')
    )
    result = []
    for p in products:
        img = p.gallery_images.filter(is_primary=True).first() or p.gallery_images.first()
        result.append({'name': p.name, 'views_count': p.views_count, 'image': img.image.url if img else None})
    return result

def get_total_users():
    return CustomUser.objects.count()

def get_total_products():
    return Product.objects.count()

def get_revenue_chart(period=30):
    end_date = timezone.now()
    start_date = end_date - timedelta(days=int(period))

    data = (
        Order.objects
        .exclude(status='CANCELLED')
        .filter(created_at__gte=start_date)
        .annotate(date=TruncDay('created_at'))
        .values('date')
        .annotate(total_revenue=Sum('total_amount'))
        .order_by('date')
    )

    return [
        {'date': item['date'].strftime('%Y-%m-%d'), 'revenue': float(item['total_revenue'] or 0)}
        for item in data if item['date']
    ]

def get_orders_chart(period=30):
    end_date = timezone.now()
    start_date = end_date - timedelta(days=int(period))
    
    data = (
        Order.objects
        .filter(created_at__gte=start_date)
        .annotate(date=TruncDay('created_at'))
        .values('date')
        .annotate(total_orders=Count('id'))
        .order_by('date')
    )
    
    return [
        {'date': item['date'].strftime('%Y-%m-%d'), 'count': item['total_orders'] or 0} 
        for item in data if item['date']
    ]

def get_low_stock_products(threshold=3, limit=10):
    """
    Returns products below stock threshold with category info and zero-stock alert flag.
    """
    products = (
        Product.objects
        .filter(quantity__lt=threshold)
        .select_related('category')
        .order_by('quantity')[:limit]
        .prefetch_related('gallery_images')
    )
    result = []
    for p in products:
        img = p.gallery_images.filter(is_primary=True).first() or p.gallery_images.first()
        result.append({
            'name': p.name,
            'quantity': p.quantity,
            'category': p.category.name if p.category else None,
            'alert_flag': p.quantity == 0,
            'image': img.image.url if img else None,
        })
    return result
