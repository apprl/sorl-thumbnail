from apparel.models import *
from django.contrib import admin
from modeltranslation.admin import TranslationAdmin


#
# Products
#

class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'category', 'gender', 'manufacturer', 'sku',)
    list_filter = ['category', 'gender', 'manufacturer', 'vendors']

admin.site.register(Product, ProductAdmin)

class LookAdmin(admin.ModelAdmin):
    raw_id_fields = ('products',)
    list_display = ('title', 'user', 'component', 'is_featured')
    list_filter = ['is_featured']

admin.site.register(Look, LookAdmin)

class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name', 'active',)
    list_filter = ['active']

admin.site.register(Manufacturer, ManufacturerAdmin)

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
    list_display = ['name', 'parent']
    list_filter = ['parent']

admin.site.register(OptionType, OptionTypeAdmin)

class OptionAdmin(admin.ModelAdmin):
    list_display = ['value', 'option_type']
    list_filter = ['option_type']

admin.site.register(Option, OptionAdmin)

admin.site.register(Vendor)

class VendorProductAdmin(admin.ModelAdmin):
    list_display = ['product', 'vendor', 'price']
    list_filter = ['vendor']

admin.site.register(VendorProduct, VendorProductAdmin)


#
# User data
#

admin.site.register(LookComponent)
admin.site.register(Wardrobe)

