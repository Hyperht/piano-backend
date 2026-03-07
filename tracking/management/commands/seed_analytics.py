import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from decimal import Decimal

from vendors.models import Vendor
from products.models import Product, Category
from orders.models import Order, OrderItem
from tracking.models import ProductViewEvent, AddToCartEvent, WishlistEvent, CheckoutEvent

User = get_user_model()

# Performance-testing seeder only — DO NOT run in production. Use clear_seed_data to remove inserted records.
class Command(BaseCommand):
    help = 'Seeds the database with 100k+ tracking events and 10k+ orders for performance testing'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting performance seeder...')
        
        # Prerequisites
        vendors = list(Vendor.objects.all())
        products = list(Product.objects.all())
        users = list(User.objects.all())
        
        if not vendors or not products or not users:
            self.stdout.write('Database must contain at least 1 Vendor, Product, and User before seeding.')
            return
            
        traffic_sources = ['utm_source=facebook', 'utm_source=google', 'direct', 'referral', 'organic_google']

        # 1. Seed 10k Orders (and checkouts)
        self.stdout.write('Seeding 10,000 Orders & Checkouts (can take a minute)...')
        orders_to_create = []
        checkouts_to_create = []

        now = timezone.now()
        for i in range(10000):
            created_at = now - timedelta(days=random.randint(0, 365))
            user = random.choice(users)
            session_id = f"sess_{random.randint(1000, 999999)}_{i}"
            ts = random.choice(traffic_sources)
            
            # Checkout Event
            checkouts_to_create.append(
                CheckoutEvent(
                    user=user,
                    session_id=session_id,
                    traffic_source=ts,
                    created_at=created_at
                )
            )
            
            # Complete Order
            order = Order(
                user=user,
                total_amount=random.uniform(20.0, 500.0), # Approximate
                status='DELIVERED',
                traffic_source=ts,
                region_snapshot=random.choice(['Cairo', 'Giza', 'Alexandria', 'Luxor']),
                created_at=created_at,
                updated_at=created_at,
            )
            orders_to_create.append(order)

        # Bulk create orders to get IDs (will need a workaround if generating order items in memory)
        # Note: bulk_create doesn't return PKs reliably in older Django/Sqlite without returning_fields
        # So we'll save them, it's 10k, it will take ~10 seconds in a batch loop.
        with transaction.atomic():
            for o in orders_to_create:
                o.save()
            CheckoutEvent.objects.bulk_create(checkouts_to_create, batch_size=2000)

        # 2. Seed Order Items
        self.stdout.write('Seeding Order Items...')
        order_items_to_create = []
        products_with_vendor = [p for p in products if p.vendor_id is not None]
        
        if not products_with_vendor:
            self.stdout.write('No products with a vendor found. OrderItems cannot be seeded.')
            return

        for order in orders_to_create:
            product = random.choice(products_with_vendor)
            current_price = product.get_current_price()
            qty = random.randint(1, 3)
            order_items_to_create.append(
                OrderItem(
                    order=order,
                    product=product,
                    vendor=product.vendor,
                    quantity=qty,
                    price_snapshot=current_price,
                    commission_amount=current_price * Decimal('0.10'),
                    subtotal=current_price * qty
                )
            )
        OrderItem.objects.bulk_create(order_items_to_create, batch_size=2000)

        # 3. Seed 100k Tracking Events (Views, Cart Adds, Wishlists)
        self.stdout.write('Seeding 100,000 Tracking Events (can take a minute)...')
        views_to_create = []
        carts_to_create = []
        wishlists_to_create = []

        for i in range(100000):
            created_at = now - timedelta(days=random.randint(0, 365))
            user = random.choice(users) if random.random() > 0.5 else None
            product = random.choice(products_with_vendor)
            session_id = f"sess_rand_{random.randint(1000, 999999)}_{i}"
            ts = random.choice(traffic_sources)

            views_to_create.append(
                ProductViewEvent(
                    user=user,
                    product=product,
                    vendor=product.vendor,
                    session_id=session_id,
                    traffic_source=ts,
                    created_at=created_at
                )
            )

            # ~10% convert to cart add
            if random.random() > 0.9:
                carts_to_create.append(
                    AddToCartEvent(
                        user=user,
                        product=product,
                        vendor=product.vendor,
                        session_id=session_id,
                        traffic_source=ts,
                        created_at=created_at
                    )
                )
                
            # ~5% convert to wishlist (only if user logged in)
            if random.random() > 0.95 and user is not None:
                wishlists_to_create.append(
                    WishlistEvent(
                        user=user,
                        product=product,
                        vendor=product.vendor,
                        traffic_source=ts,
                        created_at=created_at
                    )
                )

        ProductViewEvent.objects.bulk_create(views_to_create, batch_size=5000)
        AddToCartEvent.objects.bulk_create(carts_to_create, batch_size=5000)
        WishlistEvent.objects.bulk_create(wishlists_to_create, batch_size=5000)

        self.stdout.write(self.style.SUCCESS(f'Successfully completed performance seeding!'))
        self.stdout.write(self.style.SUCCESS(f'Total Views Inserted: {len(views_to_create)}'))
        self.stdout.write(self.style.SUCCESS(f'Total Adds To Cart Inserted: {len(carts_to_create)}'))
        self.stdout.write(self.style.SUCCESS(f'Total Wishlists Inserted: {len(wishlists_to_create)}'))
