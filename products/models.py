from django.db import models
from vendors.models import Vendor
from django.core.validators import MinValueValidator, MaxValueValidator
import re
from users.models import TimeStampedModel

def normalize_arabic(text):
    if not text:
        return ""
    text = re.sub(r"[ًٌٍَُِْـ]", "", text)
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
    return text.lower()

# -----------------------
# Colors
# -----------------------
class Color(models.Model): 
    name = models.CharField(max_length=50, unique=True) 
    hex_code = models.CharField(max_length=7, unique=True) 

    def __str__(self):
        return self.name

# -----------------------
# Categories & Subcategories
# -----------------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True) 
    image = models.ImageField(upload_to='category_images/', blank=True, null=True)
    slug = models.SlugField(max_length=100, unique=True)
    def __str__(self):
        return self.name


class Subcategory(models.Model):
    name = models.CharField(max_length=100) 
    image = models.ImageField(upload_to='subcategory_images/', blank=True, null=True)
    slug = models.SlugField(max_length=100, unique=True)
    parent_category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='subcategories'
    )

    class Meta:
        unique_together = ('name', 'parent_category')

    def __str__(self):
        return f"{self.name} ({self.parent_category.name})"

# -----------------------
# Rooms & Styles
# -----------------------
class Room(models.Model):
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to='room_images/', blank=True, null=True)
    
    def __str__(self):
        return self.name

class Style(models.Model):
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to='style_images/', blank=True, null=True)

    def __str__(self):
        return self.name


# -----------------------
# Products
# -----------------------

class ProductSpecification(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class ProductSpecificationValue(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='specification_values')
    specification = models.ForeignKey(ProductSpecification, on_delete=models.CASCADE, related_name='values')
    value = models.CharField(max_length=255)

    class Meta:
        unique_together = ('product', 'specification')

    def __str__(self):
        return f"{self.product.name} - {self.specification.name}: {self.value}"


class Product(TimeStampedModel):
    name_en_normalized = models.CharField(
        max_length=200,
        editable=False,
        db_index=True,
        null=True,
        blank=True
    )

    name_ar_normalized = models.CharField(
        max_length=200,
        editable=False,
        db_index=True,
        null=True,
        blank=True
    )
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)

    name_normalized = models.CharField(
        max_length=200,
        editable=False,
        db_index=True
    )
    description_normalized = models.TextField(
        blank=True,
        null=True,
        editable=False
    )
    short_description = models.CharField(max_length=255, blank=True, null=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    dimensions = models.CharField(max_length=255, blank=True, null=True) 
    specifications = models.JSONField(default=dict, blank=True) # New field per ER

    original_price = models.DecimalField(max_digits=10, decimal_places=2) # Kept per user req
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True) # Kept per user req
    is_on_sale = models.BooleanField(default=False)
    # created_at handled by TimeStampedModel
    rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        default=0.0
    )
    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=3)
    colors = models.ManyToManyField(Color, related_name='products', blank=True)
    rooms = models.ManyToManyField(
        Room,
        related_name='products',
        blank=True
    )
    styles = models.ManyToManyField(
        Style,
        related_name='products',
        blank=True
    )
    
    is_active = models.BooleanField(default=True)
    views_count = models.PositiveIntegerField(default=0) 

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products'
    )

    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["vendor"]),
        ]

    def get_current_price(self):
        """Returns the sale price if on sale, otherwise the original price."""
        if self.is_on_sale and self.sale_price is not None:
            return self.sale_price
        return self.original_price


    def save(self, *args, **kwargs):
        # Normalization logic
        if hasattr(self, "name_en"): # Hypothetical field based on ref, but keeping logic safely
             self.name_en_normalized = normalize_arabic(getattr(self, 'name_en', ''))
        
        if hasattr(self, "name_ar"): # Hypothetical
             self.name_ar_normalized = normalize_arabic(getattr(self, 'name_ar', ''))

        # Standard normalization for search
        self.name_normalized = normalize_arabic(self.name)
        if self.description:
            self.description_normalized = normalize_arabic(self.description)

        # Auto-deactivate if stock is zero
        if self.quantity == 0:
            self.is_active = False

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductImage(TimeStampedModel): 
    product = models.ForeignKey(
        Product,
        related_name='gallery_images',
        on_delete=models.CASCADE
    )
    is_primary = models.BooleanField(default=False)
    image = models.ImageField(upload_to='product_gallery/')
    alt_text = models.CharField(max_length=255, blank=True) 
    color = models.ForeignKey(
        Color, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='product_images'
    )
    
    def __str__(self):
        return f"Image for {self.product.name}"

#---------------------------
# Reviews
#---------------------------
class Review(TimeStampedModel):
    user = models.ForeignKey(
        'users.CustomUser', 
        on_delete=models.CASCADE, 
        related_name='reviews'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='reviews'
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True, null=True) 
    # created_at handled by TimeStampedModel
    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"Review for {self.product.name} by {self.user.username}"
