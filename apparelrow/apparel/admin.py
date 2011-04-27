from apparel.models import *
from django.contrib import admin
from modeltranslation.admin import TranslationAdmin


#
# Products
#
admin.site.register(Manufacturer)

class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'manufacturer', 'sku',)
    list_filter = ['date_added', 'vendors']

admin.site.register(Product, ProductAdmin)

class LookAdmin(admin.ModelAdmin):
    raw_id_fields = ('products',)
    list_display = ('title', 'user', 'component', 'is_featured')
    list_filter = ['is_featured']

admin.site.register(Look, LookAdmin)

class CategoryAdmin(TranslationAdmin):
    list_display = ('name', 'ancestors', 'on_front_page',)
    list_filter = ['parent', 'on_front_page']
    
    def ancestors(self, category):
        return ' > '.join([c.name for c in category.get_ancestors()])

admin.site.register(Category, CategoryAdmin)

class VendorCategoryAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'name', 'default_gender', 'category',)
    list_filter = ['vendor', 'category', 'default_gender']

admin.site.register(VendorCategory, VendorCategoryAdmin)

class OptionTypeAdmin(admin.ModelAdmin):
    list_display = ['name']

admin.site.register(Option)
admin.site.register(OptionType, OptionTypeAdmin)

admin.site.register(Vendor)
admin.site.register(VendorProduct)


#
# User data
#

admin.site.register(LookComponent)
admin.site.register(Wardrobe)

