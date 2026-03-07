import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from crm.models import CustomerProfile

logger = logging.getLogger(__name__)


class CustomerService:
    """
    Service layer for CRM domain.
    All business logic for customer metric updates lives here.
    No direct DB writes from views or handlers — only through this service.
    """

    @staticmethod
    def get_or_create_profile(user) -> CustomerProfile:
        """Ensures a CustomerProfile exists for the given user."""
        profile, created = CustomerProfile.objects.get_or_create(user=user)
        if created:
            logger.info(f"Created new CustomerProfile for user {user.id}")
        return profile

    @staticmethod
    @transaction.atomic
    def update_customer_metrics(order_id: int) -> CustomerProfile:
        """
        Updates customer metrics based on a newly created order.
        Called by CRM event handler after OrderCreatedEvent.

        Uses order snapshot data — no cross-domain writes.
        Atomic increments to avoid race conditions.
        """
        from orders.models import Order, OrderItem

        try:
            order = Order.objects.select_related('user').get(id=order_id)
        except Order.DoesNotExist:
            logger.error(f"Cannot update CRM metrics: Order {order_id} not found")
            return None

        user = order.user
        if not user:
            logger.warning(f"Order {order_id} has no associated user, skipping CRM update")
            return None

        # Calculate order total from items (snapshot data)
        order_total = Decimal('0.00')
        items = OrderItem.objects.filter(order=order)
        for item in items:
            order_total += item.subtotal

        # Get or create customer profile
        profile, created = CustomerProfile.objects.get_or_create(user=user)

        # Atomic update — no full recalculation query needed
        CustomerProfile.objects.filter(pk=profile.pk).update(
            total_spent=F('total_spent') + order_total,
            orders_count=F('orders_count') + 1,
            last_order_date=order.created_at,
            lifetime_value=F('lifetime_value') + order_total,
            region_snapshot=order.region_snapshot or profile.region_snapshot,
        )

        # Refresh from DB to get updated values
        profile.refresh_from_db()

        logger.info(
            f"CRM metrics updated for user {user.id}: "
            f"total_spent={profile.total_spent}, "
            f"orders_count={profile.orders_count}"
        )

        return profile

    @staticmethod
    @transaction.atomic
    def recalculate_customer_metrics(user) -> CustomerProfile:
        """
        Full recalculation of customer metrics from all orders.
        Use only for data correction — not for regular flow.
        """
        from orders.models import Order, OrderItem
        from django.db.models import Sum, Max, Count

        profile = CustomerService.get_or_create_profile(user)

        order_stats = Order.objects.filter(
            user=user,
            status__in=['DELIVERED', 'CONFIRMED', 'SHIPPED', 'NEW']
        ).aggregate(
            total_orders=Count('id'),
            last_date=Max('created_at'),
        )

        # Calculate total from order items for financial accuracy
        total = OrderItem.objects.filter(
            order__user=user,
            order__status__in=['DELIVERED', 'CONFIRMED', 'SHIPPED', 'NEW']
        ).aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')

        # Get most recent region
        latest_order = Order.objects.filter(
            user=user
        ).order_by('-created_at').first()

        profile.total_spent = total
        profile.orders_count = order_stats['total_orders'] or 0
        profile.last_order_date = order_stats['last_date']
        profile.lifetime_value = total
        if latest_order and latest_order.region_snapshot:
            profile.region_snapshot = latest_order.region_snapshot
        profile.save()

        logger.info(f"Full CRM recalculation for user {user.id}: total_spent={total}")

        return profile
