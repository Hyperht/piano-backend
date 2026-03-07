from decimal import Decimal
from marketing.strategies.base import BaseDiscountStrategy


class FixedDiscountStrategy(BaseDiscountStrategy):
    """Calculates fixed-amount discount. No DB writes."""

    def calculate(self, cart_subtotal: Decimal, discount_value: Decimal) -> Decimal:
        """
        Returns the fixed discount value, capped at cart subtotal.
        """
        if discount_value <= Decimal('0'):
            return Decimal('0.00')

        discount = discount_value

        # Discount cannot exceed subtotal
        if discount > cart_subtotal:
            discount = cart_subtotal

        return discount.quantize(Decimal('0.01'))
