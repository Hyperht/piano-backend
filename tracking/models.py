from django.db import models
from users.models import CustomUser
from products.models import Product
from vendors.models import Vendor

class ProductViewEvent(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    
    session_id = models.CharField(max_length=255, db_index=True)
    traffic_source = models.CharField(max_length=50, db_index=True, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["vendor", "created_at"]),
            models.Index(fields=["session_id"]),
        ]

class AddToCartEvent(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    
    session_id = models.CharField(max_length=255, db_index=True)
    traffic_source = models.CharField(max_length=50, db_index=True, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["vendor", "created_at"]),
            models.Index(fields=["session_id"]),
        ]

class WishlistEvent(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    
    traffic_source = models.CharField(max_length=50, db_index=True, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["vendor", "created_at"]),
        ]

class CheckoutEvent(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=255, db_index=True)
    traffic_source = models.CharField(max_length=50, db_index=True, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["session_id"]),
        ]
