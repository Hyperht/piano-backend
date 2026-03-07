from django.db import models
from users.models import CustomUser, TimeStampedModel
from vendors.models import Vendor
from django.core.validators import MinValueValidator, MaxValueValidator


class Coupon(TimeStampedModel):
    DISCOUNT_TYPE_CHOICES = [
        ('PERCENTAGE', 'Percentage'),
        ('FIXED', 'Fixed'),
    ]

    code = models.CharField(max_length=50, unique=True, db_index=True)
    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_TYPE_CHOICES,
        default='PERCENTAGE'
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_purchase = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    max_uses = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Global usage limit for this coupon"
    )
    used_count = models.PositiveIntegerField(
        default=0,
        help_text="Atomically incremented on each usage"
    )
    per_user_limit = models.PositiveIntegerField(null=True, blank=True)
    vendor = models.ForeignKey(
        Vendor, on_delete=models.CASCADE,
        related_name='coupons',
        null=True, blank=True,
        help_text="If set, coupon is scoped to this vendor"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['vendor']),
            models.Index(fields=['valid_from']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_active', 'valid_from', 'expires_at']),
        ]

    def __str__(self):
        return self.code


class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='coupon_usages')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='coupon_usages')
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['coupon', 'user']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.coupon.code} used by {self.user.username}"
