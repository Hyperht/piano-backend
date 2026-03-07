"""
Base discount strategy — Strategy Pattern for coupon discount calculation.
Strategies only calculate discount amounts. No DB writes.
"""
from abc import ABC, abstractmethod
from decimal import Decimal


class BaseDiscountStrategy(ABC):
    """Abstract base class for discount calculation strategies."""

    @abstractmethod
    def calculate(self, cart_subtotal: Decimal, discount_value: Decimal) -> Decimal:
        """
        Calculate the discount amount.
        
        Args:
            cart_subtotal: The subtotal of the cart before discount.
            discount_value: The raw value of the discount (percentage or fixed amount).
            
        Returns:
            The calculated discount amount (always positive, capped at cart_subtotal).
        """
        pass
