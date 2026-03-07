from django.core.management.base import BaseCommand
from django.db import transaction


# Safely removes all records created by seed_analytics. Use this to reset a performance-test DB.
class Command(BaseCommand):
    help = 'Removes all tracking events and optionally seeded orders from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--include-orders',
            action='store_true',
            help='Also delete Order and OrderItem records that have a region_snapshot set (seeded by seed_analytics)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show counts of records that would be deleted without actually deleting them',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from tracking.models import ProductViewEvent, AddToCartEvent, WishlistEvent, CheckoutEvent

        dry_run = options['dry_run']

        view_count = ProductViewEvent.objects.count()
        cart_count = AddToCartEvent.objects.count()
        wishlist_count = WishlistEvent.objects.count()
        checkout_count = CheckoutEvent.objects.count()

        self.stdout.write(f'ProductViewEvent:  {view_count}')
        self.stdout.write(f'AddToCartEvent:    {cart_count}')
        self.stdout.write(f'WishlistEvent:     {wishlist_count}')
        self.stdout.write(f'CheckoutEvent:     {checkout_count}')

        if options['include_orders']:
            from orders.models import Order
            seeded_orders = Order.objects.exclude(region_snapshot__isnull=True).exclude(region_snapshot='')
            order_count = seeded_orders.count()
            self.stdout.write(f'Seeded Orders:     {order_count}')

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run — no records deleted.'))
            return

        ProductViewEvent.objects.all().delete()
        AddToCartEvent.objects.all().delete()
        WishlistEvent.objects.all().delete()
        CheckoutEvent.objects.all().delete()

        if options['include_orders']:
            from orders.models import Order
            deleted_orders, _ = Order.objects.exclude(
                region_snapshot__isnull=True
            ).exclude(region_snapshot='').delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {deleted_orders} seeded orders and their items.'))

        self.stdout.write(self.style.SUCCESS(
            f'Cleared {view_count} views, {cart_count} cart adds, '
            f'{wishlist_count} wishlists, {checkout_count} checkouts.'
        ))
