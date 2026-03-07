from django.contrib import admin
from modeltranslation.admin import TabbedTranslationAdmin, TranslationTabularInline
from .models import (
    PromoBanner,
    HeroSlide,
    CustomUser,
    PromoGridCategory,
    Favorite,
    Governorate,
    Area,
    Address,
    ContactMessage,
)

# -----------------------
# Promo Banner Admin
# -----------------------
@admin.register(PromoBanner)
class PromoBannerAdmin(admin.ModelAdmin):
    list_display = ('name', 'end_date', 'is_active')
    list_filter = ('is_active',)


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
    # Replaced 'added_at' with 'created_at' to resolve E035 error.
    # Note: Favorite model in users.models (from view) had 'created_at' from TimeStampedModel.
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
    list_display = ('user', 'street_address', 'area', 'get_governorate_name', 'is_default')
    list_filter = ('is_default', 'area__governorate')
    search_fields = ('user__username', 'street_address', 'phone_number_1') # Updated field name to phone_number_1

    def get_governorate_name(self, obj):
        """Displays the Governorate name by traversing Address -> Area -> Governorate."""
        return obj.area.governorate.name if obj.area and obj.area.governorate else 'N/A'
    get_governorate_name.short_description = 'Governorate'


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