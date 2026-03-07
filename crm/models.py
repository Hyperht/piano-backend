from django.db import models
from users.models import CustomUser


class CustomerProfile(models.Model):
    """
    Read-optimized customer intelligence snapshot.
    Updated via events — never dynamically calculated.
    No business logic in this model.
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='customer_profile'
    )
    total_spent = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00,
        help_text="Snapshot-aggregated total from delivered orders"
    )
    orders_count = models.PositiveIntegerField(
        default=0,
        help_text="Incremented atomically via OrderCreatedEvent"
    )
    last_order_date = models.DateTimeField(blank=True, null=True)
    region_snapshot = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Last known region from the most recent order"
    )
    lifetime_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00,
        help_text="Calculated LTV metric (can factor returns/discounts)"
    )
    loyalty_score = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['total_spent']),
            models.Index(fields=['region_snapshot']),
            models.Index(fields=['created_at']),
            models.Index(fields=['-total_spent']),  # For top customers ranking
        ]

    def __str__(self):
        return f"Profile for {self.user.username}"
