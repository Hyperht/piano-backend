from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDay
from django.utils import timezone
from datetime import timedelta
from users.models import CustomUser, Order, Product, OrderItem, Favorite

def get_revenue_metrics():
    return Order.objects.filter(status='DELIVERED').aggregate(total=Sum('final_total'))['total'] or 0

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
    return (
        OrderItem.objects
        .values('product__name', 'product__image') 
        .annotate(sales_count=Sum('quantity'), revenue=Sum(F('quantity') * F('price_at_purchase')))
        .order_by('-sales_count')[:limit]
    )

def get_recent_orders(limit=5):
    return (
        Order.objects
        .select_related('user')
        .order_by('-created_at')[:limit]
        .annotate(user_email=F('user__email'))
        .values('id', 'user_email', 'status', 'final_total', 'created_at')
    )

def get_most_wishlisted(limit=5):
    return (
        Product.objects
        .annotate(wishlist_count=Count('favorite'))
        .filter(wishlist_count__gt=0)
        .order_by('-wishlist_count')[:limit]
        .values('name', 'image', 'wishlist_count')
    )

def get_most_watched(limit=5):
    return (
        Product.objects
        .filter(views__gt=0)
        .order_by('-views')[:limit]
        .values('name', 'image', 'views')
    )

def get_total_users():
    return CustomUser.objects.count()

def get_total_products():
    return Product.objects.count()

def get_revenue_chart(period=30):
    end_date = timezone.now()
    start_date = end_date - timedelta(days=int(period))
    
    data = (
        Order.objects
        .filter(status='DELIVERED', created_at__gte=start_date)
        .annotate(date=TruncDay('created_at'))
        .values('date')
        .annotate(revenue=Sum('final_total'))
        .order_by('date')
    )
    
    return [
        {'date': item['date'].strftime('%Y-%m-%d'), 'revenue': item['revenue']}
        for item in data
    ]

def get_orders_chart(period=30):
    end_date = timezone.now()
    start_date = end_date - timedelta(days=int(period))
    
    data = (
        Order.objects
        .filter(created_at__gte=start_date)
        .annotate(date=TruncDay('created_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    
    return [
        {'date': item['date'].strftime('%Y-%m-%d'), 'count': item['count']} 
        for item in data
    ]

def get_low_stock_products(threshold=3, limit=5):
    return (
        Product.objects
        .filter(quantity__lt=threshold)
        .order_by('quantity')[:limit]
        .values('name', 'image', 'quantity')
    )
