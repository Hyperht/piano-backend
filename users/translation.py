from modeltranslation.translator import register, TranslationOptions
from .models import Product, Category, ProductImage, HeroSlide, Subcategory, PromoGridCategory, Room, Style, Area, Governorate

@register(Product)
class ProductTranslationOptions(TranslationOptions):
    fields = ('name', 'short_description', 'description',)

@register(Category)
class CategoryTranslationOptions(TranslationOptions):
    fields = ('name',)

@register(Subcategory)
class SubcategoryTranslationOptions(TranslationOptions):
    fields = ('name',)

@register(ProductImage)
class ProductImageTranslationOptions(TranslationOptions):
    fields = ('alt_text',)

@register(HeroSlide)
class HeroSlideTranslationOptions(TranslationOptions):
    fields = ('title', 'subtitle', 'button_text')

@register(PromoGridCategory)
class PromoGridCategoryTranslationOptions(TranslationOptions):
    fields = ('title', 'subtitle')


@register(Room)
class RoomTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Style)
class StyleTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Governorate)
class GovernorateTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Area)
class AreaTranslationOptions(TranslationOptions):
    fields = ('name',)
