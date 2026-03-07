from django.db import models
from products.models import Product


class StockMovement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')
    change_amount = models.IntegerField()
    reason = models.CharField(max_length=255, choices=[
        ('ORDER', 'Order'),
        ('RETURN', 'Return'),
        ('DAMAGE', 'Damage'),
        ('THEFT', 'Theft'),
        ('MANUAL', 'Manual Adjustment'),
        ('OTHER', 'Other'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['product', 'created_at']),
            models.Index(fields=['reason']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.change_amount}"
