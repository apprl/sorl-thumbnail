from apparel.models import *
from django.contrib import admin


#
# Products
#
admin.site.register(Manufacturer)

class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'manufacturer', 'sku',)
    list_filter = ['date_added', 'vendors']

admin.site.register(Product, ProductAdmin)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'on_front_page',)

admin.site.register(Category, CategoryAdmin)

class VendorCategoryAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'name', 'category',)

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

admin.site.register(Look)
admin.site.register(LookComponent)
admin.site.register(Wardrobe)

