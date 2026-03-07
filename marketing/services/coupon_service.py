import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.core.exceptions import ValidationError

from marketing.models import Coupon, CouponUsage
from marketing.strategies.percentage import PercentageDiscountStrategy
from marketing.strategies.fixed import FixedDiscountStrategy
from orders.models import Order
from users.models import CustomUser

logger = logging.getLogger(__name__)

# Strategy registry — no if/else explosion
_STRATEGY_MAP = {
    'PERCENTAGE': PercentageDiscountStrategy(),
    'FIXED': FixedDiscountStrategy(),
}


class CouponService:
    """
    Service layer for coupon operations.
    Uses Strategy Pattern for discount calculation.
    All writes go through this service — never from views directly.
    """

    @staticmethod
    def _get_strategy(discount_type: str):
        """Factory method to get the appropriate discount strategy."""
        strategy = _STRATEGY_MAP.get(discount_type)
        if not strategy:
            raise ValidationError(f"Unknown discount type: {discount_type}")
        return strategy

    @staticmethod
    def validate_and_calculate_discount(
        coupon_code: str,
        cart_subtotal: Decimal,
        user: CustomUser
    ) -> dict:
        """
        Validates a coupon code against a cart subtotal and user.
        Returns a dict with 'coupon' instance and 'discount_amount'.
        Raises ValidationError if invalid.
        """
        if not coupon_code:
            return {'coupon': None, 'discount_amount': Decimal('0.00')}

        try:
            coupon = Coupon.objects.get(
                code__iexact=coupon_code,
                is_active=True,
                valid_from__lte=timezone.now(),
                expires_at__gte=timezone.now()
            )
        except Coupon.DoesNotExist:
            raise ValidationError("Invalid or expired coupon code.")

        # Minimum purchase check
        if coupon.min_purchase and cart_subtotal < coupon.min_purchase:
            raise ValidationError(
                f"Minimum purchase of {coupon.min_purchase} required for this coupon."
            )

        # Global usage limit check
        if coupon.max_uses is not None:
            if coupon.used_count >= coupon.max_uses:
                raise ValidationError("This coupon has reached its usage limit.")

        # Per-user limit check
        if coupon.per_user_limit is not None:
            user_usages = coupon.usages.filter(user=user).count()
            if user_usages >= coupon.per_user_limit:
                raise ValidationError("You have reached the usage limit for this coupon.")

        # Use strategy pattern for discount calculation — no if/else
        strategy = CouponService._get_strategy(coupon.discount_type)
        discount_amount = strategy.calculate(cart_subtotal, coupon.discount_value)

        logger.info(
            f"Coupon {coupon.code} validated: {coupon.discount_type} "
            f"discount of {discount_amount} on subtotal {cart_subtotal}"
        )

        return {
            'coupon': coupon,
            'discount_amount': discount_amount,
        }

    @staticmethod
    @transaction.atomic
    def record_usage(
        coupon: Coupon,
        user: CustomUser,
        order: Order,
        discount_applied: Decimal
    ) -> CouponUsage:
        """
        Records the usage of a coupon after a successful order placement.
        Atomically increments used_count.
        """
        if not coupon:
            return None

        usage = CouponUsage.objects.create(
            coupon=coupon,
            user=user,
            order=order,
            discount_applied=discount_applied
        )

        # Atomic increment of used_count
        Coupon.objects.filter(pk=coupon.pk).update(
            used_count=F('used_count') + 1
        )

        logger.info(
            f"Recorded coupon usage: {coupon.code} by user {user.id} "
            f"on order {order.id}, discount: {discount_applied}"
        )

        return usage
