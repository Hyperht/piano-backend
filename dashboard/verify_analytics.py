import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'piano.settings')
django.setup()

from dashboard.analytics.services import DashboardService
from users.models import Product
import json
import json

def verify():
    print("Verifying Analytics...")
    data = DashboardService.get_aggregated_analytics()
    print("Keys found:", data.keys())
    print("Total Revenue:", data['total_revenue'])
    print("Total Orders:", data['total_orders'])
    print("Recent Orders Count:", len(data['recent_orders']))
    
    print("\nVerifying Charts...")
    rev_chart = DashboardService.get_revenue_chart(30)
    print("Revenue Chart Data Points:", len(rev_chart))
    if rev_chart:
        print("Sample:", rev_chart[0])
        
    ord_chart = DashboardService.get_orders_chart(30)
    print("Orders Chart Data Points:", len(ord_chart))

if __name__ == '__main__':
    verify()
