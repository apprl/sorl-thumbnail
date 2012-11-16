from modeltranslation.translator import translator, TranslationOptions
from django.db.models.loading import get_model

class CategoryTranslationOptions(TranslationOptions):
    fields = ('name', 'name_order', 'singular_name')

translator.register(get_model('apparel', 'Category'), CategoryTranslationOptions)
