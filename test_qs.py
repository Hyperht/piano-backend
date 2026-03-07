import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'piano.settings')
django.setup()

from orders.selectors.orders import get_all_orders_with_customer
import json
from django.core.serializers.json import DjangoJSONEncoder

print("Starting query...")
qs = list(get_all_orders_with_customer()[:2])
print(json.dumps(qs, cls=DjangoJSONEncoder, indent=2))
