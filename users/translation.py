from modeltranslation.translator import register, TranslationOptions
from .models import HeroSlide, PromoGridCategory, Area, Governorate



@register(HeroSlide)
class HeroSlideTranslationOptions(TranslationOptions):
    fields = ('title', 'subtitle', 'button_text')

@register(PromoGridCategory)
class PromoGridCategoryTranslationOptions(TranslationOptions):
    fields = ('title', 'subtitle')





@register(Governorate)
class GovernorateTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Area)
class AreaTranslationOptions(TranslationOptions):
    fields = ('name',)
