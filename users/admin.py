from django.contrib import admin
from modeltranslation.admin import TabbedTranslationAdmin, TranslationTabularInline
# from django import forms
# from PIL import Image
from .models import (
    PromoBanner,
    Category,
    Subcategory,
    HeroSlide,
    Product,
    Color,
    CustomUser,
    Room,
    Style,
    PromoGridCategory,
    Cart,
    CartItem,
    Favorite,
    # --- Updated Imports ---
    Governorate,
    Area,
    Address,
    ProductImage,
    Review,
    Order,
    OrderItem,
    ContactMessage,
)

# -----------------------
# Product Image Inline
# -----------------------
class ProductImageInline(TranslationTabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'color') 
    raw_id_fields = ('color',)


# -----------------------
# Product Admin
# -----------------------
# class ProductAdminForm(forms.ModelForm):
#     class Meta:
#         model = Product
#         fields = '__all__'
#
#     def clean_image(self):
#         image = self.cleaned_data.get('image', False)
#         if image:
#             img = Image.open(image)
#             if img.width > 310 or img.height > 216:
#                 raise forms.ValidationError("Image dimensions should not be larger than 310x216 pixels.")
#         return image


@admin.register(Product)
class ProductAdmin(TabbedTranslationAdmin):
    # form = ProductAdminForm
    list_display = (
        'name',
        'category',
        'subcategory',
        'original_price',
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
        'image',
        ('original_price', 'sale_price', 'is_on_sale'),
        'sale_badge_image',
        'rating',
        'colors',
        'rooms',
        'styles',
    )


# -----------------------
# Color Admin
# -----------------------
@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'hex_code')


# -----------------------
# Promo Banner Admin
# -----------------------
@admin.register(PromoBanner)
class PromoBannerAdmin(admin.ModelAdmin):
    list_display = ('name', 'end_date', 'is_active')
    list_filter = ('is_active',)


# -----------------------
# Subcategory Inline for Category
# -----------------------
class SubcategoryInline(admin.TabularInline):
    model = Subcategory
    extra = 1


# -----------------------
# Category Admin
# -----------------------
@admin.register(Category)
class CategoryAdmin(TabbedTranslationAdmin):
    list_display = ('name',)
    fields = ('name', 'image')
    inlines = [SubcategoryInline]


# -----------------------
# Subcategory Admin
# -----------------------
@admin.register(Subcategory)
class SubcategoryAdmin(TabbedTranslationAdmin):
    list_display = ('name', 'parent_category', 'image')
    list_filter = ('parent_category',)
    search_fields = ('name',)
    fields = ('name', 'image', 'parent_category')


# -----------------------
# Hero Slide Admin
# -----------------------
@admin.register(HeroSlide)
class HeroSlideAdmin(TabbedTranslationAdmin):
    list_display = ('name', 'is_active', 'order')
    list_filter = ('is_active',)
    list_editable = ('is_active', 'order')


# -----------------------
# Favorite Inline for CustomUser
# -----------------------
class FavoriteInline(admin.TabularInline):
    model = Favorite
    extra = 0
    # ✅ FIX: Replaced 'added_at' with 'created_at' to resolve E035 error.
    readonly_fields = ('product', 'created_at')
    fields = ('product', 'created_at')
    can_delete = True
    verbose_name = "Favorite"
    verbose_name_plural = "Favorites"


# -----------------------
# Custom User Admin Inlines
# -----------------------
class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    # Area must be displayed, not governorate directly
    fields = ('area', 'street_address', 'is_default')
    # Use raw_id_fields for Area if you have many areas
    raw_id_fields = ('area',) 
    verbose_name = "User Address"
    verbose_name_plural = "User Addresses"


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'name', 'phone_number')
    search_fields = ('username', 'email', 'name')
    inlines = [FavoriteInline, AddressInline]


# -----------------------
# Register Room and Style Models
# -----------------------
@admin.register(Room)
class RoomAdmin(TabbedTranslationAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Style)
class StyleAdmin(TabbedTranslationAdmin):
    list_display = ('name',)
    search_fields = ('name',)


# -----------------------
# Register Promo Grid Categories
# -----------------------
@admin.register(PromoGridCategory)
class PromoGridCategoryAdmin(TabbedTranslationAdmin):
    list_display = ('title', 'subtitle', 'image', 'background_color', 'is_active', 'order')
    list_filter = ('is_active',)
    list_editable = ('is_active', 'order')
    search_fields = ('title', 'subtitle')
    fields = (
        ('title', 'subtitle'),
        ('image', 'background_color'),
        ('is_active', 'order')
    )


# -----------------------
# Shopping Cart Admin
# -----------------------
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('product',)
    fields = ('product', 'quantity',)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('user__username', 'user__email')
    inlines = [CartItemInline]
    readonly_fields = ('user', 'created_at', 'updated_at')

# -----------------------
# Location & Address Admin
# -----------------------

class AreaInline(TranslationTabularInline):
    model = Area
    extra = 1
    fields = ('name', 'shipping_cost')

@admin.register(Governorate)
class GovernorateAdmin(TabbedTranslationAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    inlines = [AreaInline]

@admin.register(Area)
class AreaAdmin(TabbedTranslationAdmin):
    list_display = ('name', 'governorate', 'shipping_cost')
    list_filter = ('governorate',)
    search_fields = ('name',)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    # Already fixed: uses callable method
    list_display = ('user', 'street_address', 'area', 'get_governorate_name', 'is_default')
    
    # Already fixed: uses field traversal
    list_filter = ('is_default', 'area__governorate')
    search_fields = ('user__username', 'street_address', 'phone_number')

    def get_governorate_name(self, obj):
        """Displays the Governorate name by traversing Address -> Area -> Governorate."""
        return obj.area.governorate.name if obj.area and obj.area.governorate else 'N/A'
    get_governorate_name.short_description = 'Governorate'

# -----------------------
# Order Admin
# -----------------------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price_at_purchase')
    fields = ('product', 'quantity', 'price_at_purchase')
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'final_total', 'created_at')
    list_filter = ('status',)
    list_editable = ('status',)
    search_fields = ('id', 'user__username')
    inlines = [OrderItemInline]
    readonly_fields = (
        'user', 
        'shipping_address', 
        'cart_subtotal', 
        'shipping_cost', 
        'coupon_discount', 
        'final_total', 
        'coupon_code_used', 
        'payment_method', 
        'payment_status', 
        'transaction_id', 
        'created_at', 
        'updated_at'
    )

    fieldsets = (
        (None, {
            'fields': ('status', 'user', 'shipping_address')
        }),
        ('Financials', {
            'fields': ('cart_subtotal', 'shipping_cost', 'coupon_discount', 'final_total', 'coupon_code_used')
        }),
        ('Payment', {
            'fields': ('payment_method', 'payment_status', 'transaction_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

# -----------------------
# Contact Message Admin
# -----------------------
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at')
    readonly_fields = ('name', 'email', 'subject', 'message', 'created_at', 'updated_at')
    search_fields = ('name', 'email', 'subject', 'message')
    list_filter = ('created_at',)

    fieldsets = (
        (None, {
            'fields': ('name', 'email', 'subject', 'created_at')
        }),
        ('Message', {
            'fields': ('message',)
        }),
    )