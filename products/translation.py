from modeltranslation.translator import register, TranslationOptions
from .models import Product, Category, Subcategory, ProductImage, Room, Style

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

@register(Room)
class RoomTranslationOptions(TranslationOptions):
    fields = ('name',)

@register(Style)
class StyleTranslationOptions(TranslationOptions):
    fields = ('name',)
