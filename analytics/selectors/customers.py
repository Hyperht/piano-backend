from django.db.models import Sum, Count, F
from orders.models import Order

def get_top_customers_summary(limit=5, start_date=None, end_date=None):
    queryset = Order.objects.exclude(status="CANCELLED")

    if start_date and end_date:
        queryset = queryset.filter(created_at__range=[start_date, end_date])

    raw_stats = list(
        queryset
        .values("user_id")
        .annotate(
            total_spent=Sum("total_amount"),
            total_orders=Count("id"),
            user_name=F("user__name"),
            u_first_name=F("user__first_name"),
            u_last_name=F("user__last_name"),
            u_username=F("user__username"),
            id=F("user_id")
        )
        .values("id", "user_name", "u_first_name", "u_last_name", "u_username", "total_spent", "total_orders")
        .order_by("-total_spent")[:limit]
    )

    results = []
    for s in raw_stats:
        first = s['u_first_name']
        last = s['u_last_name']
        
        # Fallback Logic
        if not first and not last:
            if s['user_name']:
                # Try to split full name if it exists
                parts = s['user_name'].split(' ', 1)
                first = parts[0]
                last = parts[1] if len(parts) > 1 else ""
            else:
                first = s['u_username']
                last = ""

        results.append({
            'id': s['id'],
            'first_name': first,
            'last_name': last,
            'total_spent': float(s['total_spent']),
            'total_orders': s['total_orders']
        })
    return results
