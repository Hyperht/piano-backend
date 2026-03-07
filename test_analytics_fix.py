import os
import django
import sys

# Setup django
sys.path.append('/home/youssef/freelance/Piano Project/piano-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'piano.settings')
django.setup()

from django.db.models import Sum, Count, F
from orders.models import Order, OrderItem
from analytics.selectors.aggregations import get_top_products
from analytics.selectors.customers import get_top_customers_summary

print("Testing Top Products...")
products = get_top_products(limit=5)
print(f"Count: {len(products)}")
for p in products:
    print(p)

print("\nTesting Top Customers...")
try:
    customers = get_top_customers_summary(limit=5)
    print(f"Count: {len(customers)}")
    for c in customers:
        print(c)
except Exception as e:
    print(f"Error in Top Customers: {e}")
