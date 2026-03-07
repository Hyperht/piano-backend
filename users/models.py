from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.utils import timezone # Added import
from django.db.models import Q

import re

def normalize_arabic(text):
    if not text:
        return ""
    text = re.sub(r"[ًٌٍَُِْـ]", "", text)
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
    return text.lower()

# -----------------------
# Abstract Base Models
# -----------------------
class TimeStampedModel(models.Model):
    """Abstract base class that provides self-updating 'created_at' and 'updated_at' fields."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        
# -----------------------
# Custom User (No change needed)
# -----------------------
class CustomUser(AbstractUser):
    name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(unique=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.email if self.email else self.username





# -----------------------
# Promotions
# -----------------------
class PromoBanner(models.Model):
    name = models.CharField(max_length=100, help_text="A name for internal reference")
    background_image = models.ImageField(upload_to='promo/backgrounds/', blank=True, null=True)
    left_image = models.ImageField(upload_to='promo/artworks/', blank=True, null=True)
    right_image = models.ImageField(upload_to='promo/artworks/', blank=True, null=True)
    end_date = models.DateTimeField(help_text="The date and time when the promotion ends.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# -----------------------
# Hero Slides
# -----------------------
class HeroSlide(models.Model):
    name = models.CharField(
        max_length=100,
        help_text="A name for internal reference (e.g., 'Summer Sale Banner')",
        default="Hero Slide"
    )
    title = models.CharField(max_length=200, blank=True, null=True)
    subtitle = models.CharField(max_length=300, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    short_description = models.CharField(max_length=255, blank=True, null=True)
    
    image = models.ImageField(upload_to='hero_slides/')
    button_text = models.CharField(max_length=50, blank=True, null=True)
    button_link = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    def __str__(self):
        return self.name

# -----------------------
# New Model for Promotional Grids
# -----------------------
class PromoGridCategory(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True) # Retaining the 'name' field
    description = models.TextField(blank=True, null=True)
    short_description = models.CharField(max_length=255, blank=True, null=True)
    
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=200, blank=True, null=True)
    image = models.ImageField(upload_to='promo_grid_images/')
    background_color = models.CharField(max_length=7, default='#000000', help_text="Hex code for the color overlay")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Determines the display order in the grid")

    class Meta:
        verbose_name_plural = "Promo Grid Categories"
        ordering = ['order']

    def __str__(self):
        return self.title

# -----------------------
# Address & Location Models
# -----------------------
class Governorate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        verbose_name_plural = "Governorates"

    def __str__(self):
        return self.name

class Area(models.Model):
    name = models.CharField(max_length=100)
    governorate = models.ForeignKey(
        Governorate,
        on_delete=models.CASCADE,
        related_name='areas'
    )
    shipping_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00
    )

    class Meta:
        unique_together = ('name', 'governorate')
        verbose_name_plural = "Areas"

    def __str__(self):
        return f"{self.name}, {self.governorate.name}"

class Address(TimeStampedModel): # Applied TimeStampedModel
    """
    Stores a user's saved shipping or billing addresses.
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number_1 = models.CharField(max_length=15)
    phone_number_2 = models.CharField(max_length=15, blank=True, null=True)
    street_address = models.CharField(max_length=255)
    apartment_details = models.CharField(max_length=255, blank=True, null=True)
    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        related_name='addresses_used',
    )
    
    is_default = models.BooleanField(default=False)
    class Meta:
        verbose_name_plural = "Addresses"
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=Q(is_default=True),
                name='unique_default_address_per_user'
            )
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}'s address"


# -----------------------
# User Favorites
# -----------------------
class Favorite(TimeStampedModel): # Applied TimeStampedModel
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE
    )
    # added_at is handled by TimeStampedModel

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f'{self.user.username} favorites {self.product.name}'


# -----------------------
# Contact Us Messages
# -----------------------
class ContactMessage(TimeStampedModel):
    """Model to store messages from the contact us page."""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()

    def __str__(self):
        return self.subject
# -----------------------
# Promo Banners
# -----------------------
