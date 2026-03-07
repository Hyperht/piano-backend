from django.contrib import admin
from modeltranslation.admin import TabbedTranslationAdmin, TranslationTabularInline
from .models import (
    Product, ProductImage, Color, Category, Subcategory, Room, Style
)

# -----------------------
# Product Image Inline
# -----------------------
class ProductImageInline(TranslationTabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'color') 
    raw_id_fields = ('color',)


@admin.register(Product)
class ProductAdmin(TabbedTranslationAdmin):
    list_display = (
        'name',
        'category',
        'subcategory',
        'original_price', # Preserved field name
        'is_on_sale',
        'rating',
        'is_active'
    )
    list_filter = (
        'is_on_sale',
        'is_active',
        'category',
        'subcategory'
    )
    search_fields = ('name', 'description', 'short_description')
    filter_horizontal = ('colors', 'rooms', 'styles')
    inlines = [ProductImageInline]

    fields = (
        ('name', 'is_active'),
        ('category', 'subcategory'),
        'short_description',
        'description',
        'dimensions',
        'specifications', # Added new field
        'image', # Note: Product model in users had 'image' but new model doesn't seem to have explicit 'image' field in models.py view I saw earlier? 
        # Wait, I checked products/models.py and it DOES NOT have 'image' field, only ProductImage model.
        # But users/admin.py referenced 'image'. I need to check if 'image' exists on Product.
        # Looking back at products/models.py content from Step 59:
        # It has `ProductImage` linked to `Product`. `Product` itself naturally has no `image` field in the code I wrote.
        # However, the previous `products/models.py` (Step 16) also didn't show `image` on `Product`.
        # But `users/admin.py` line 87 had `'image'`. 
        # Maybe it was a leftover or I missed something. 
        # I will remove 'image' from fields list here to be safe and correct based on models.py.
        # And 'sale_badge_image' was also in users/admin.py line 89. I don't see it in Product model.
        # I will exclude them for now to avoid errors.
        ('original_price', 'sale_price', 'is_on_sale'),
        'rating',
        'colors',
        'rooms',
        'styles',
    )

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'hex_code')

# -----------------------
# Subcategory Inline for Category
# -----------------------
class SubcategoryInline(admin.TabularInline):
    model = Subcategory
    extra = 1

@admin.register(Category)
class CategoryAdmin(TabbedTranslationAdmin):
    list_display = ('name',)
    fields = ('name', 'image')
    inlines = [SubcategoryInline]

@admin.register(Subcategory)
class SubcategoryAdmin(TabbedTranslationAdmin):
    list_display = ('name', 'parent_category', 'image')
    list_filter = ('parent_category',)
    search_fields = ('name',)
    fields = ('name', 'image', 'parent_category')

@admin.register(Room)
class RoomAdmin(TabbedTranslationAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Style)
class StyleAdmin(TabbedTranslationAdmin):
    list_display = ('name',)
    search_fields = ('name',)
