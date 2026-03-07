from decimal import Decimal
from marketing.strategies.base import BaseDiscountStrategy


class PercentageDiscountStrategy(BaseDiscountStrategy):
    """Calculates percentage-based discount. No DB writes."""

    def calculate(self, cart_subtotal: Decimal, discount_value: Decimal) -> Decimal:
        """
        Calculates discount as a percentage of cart subtotal.
        Capped at 100% (cart_subtotal).
        """
        if discount_value <= Decimal('0'):
            return Decimal('0.00')

        discount = cart_subtotal * (discount_value / Decimal('100.0'))

        # Discount cannot exceed subtotal
        if discount > cart_subtotal:
            discount = cart_subtotal

        return discount.quantize(Decimal('0.01'))
