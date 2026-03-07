from django.db import models

class DailySalesSummary(models.Model):
    date = models.DateField(unique=True)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_orders = models.PositiveIntegerField(default=0)
    total_views = models.PositiveIntegerField(default=0)
    total_add_to_cart = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Sales Summary - {self.date}"
