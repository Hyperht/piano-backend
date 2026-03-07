from django.db import models
from vendors.models import Vendor
from users.models import CustomUser, Address
from products.models import Product
from decimal import Decimal


# -----------------------
# Shopping Cart
# -----------------------
class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_cart_total(self):
        total = Decimal('0.00')
        for item in self.items.all():
            total += item.get_total_price()
        return total

    def __str__(self):
        return f"Cart for {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def get_total_price(self):
        if hasattr(self.product, 'get_current_price'):
            return self.quantity * self.product.get_current_price()
        return self.quantity * self.product.original_price

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"


# -----------------------
# Order Models
# -----------------------
class Order(models.Model):
    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('RETURNED', 'Returned'),
        ('CANCELLED', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    user = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL,
        null=True, related_name='orders'
    )
    # Dual address support: legacy FK + new shipping_address FK
    address = models.ForeignKey(
        Address, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='orders'
    )
    shipping_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='shipping_orders'
    )

    # Financials
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00')
    )
    final_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text="Final amount after discounts and shipping"
    )
    cart_subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00')
    )
    shipping_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00')
    )
    coupon_discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00')
    )

    # Coupon tracking
    coupon_code_used = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="Snapshot of coupon code used at checkout",
        db_index=True
    )

    # Payment
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES,
        default='PENDING'
    )
    transaction_id = models.CharField(max_length=255, blank=True, null=True)

    # Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    traffic_source = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    region_snapshot = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['payment_status']),
        ]

    def __str__(self):
        username = self.user.username if self.user else 'Deleted User'
        return f"Order {self.id} - {username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='order_items')

    quantity = models.PositiveIntegerField(default=1)
    price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(fields=['vendor']),
            models.Index(fields=['order', 'product']),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product.name if self.product else 'Deleted Product'}"
