from modeltranslation.translator import translator, TranslationOptions
from apparel.models import Category

class CategoryTranslationOptions(TranslationOptions):
    fields = ('name', 'name_order')

translator.register(Category, CategoryTranslationOptions)
