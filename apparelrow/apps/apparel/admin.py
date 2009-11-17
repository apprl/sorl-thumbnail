from apparel.models import *
from django.contrib import admin

admin.site.register(Manufacturer)


class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'manufacturer', 'sku',)

admin.site.register(Product, ProductAdmin)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

admin.site.register(Category, CategoryAdmin)

admin.site.register(Look)

admin.site.register(Option)

class OptionTypeAdmin(admin.ModelAdmin):
    list_display = ['name']


admin.site.register(OptionType, OptionTypeAdmin)

admin.site.register(Vendor)
admin.site.register(VendorProduct)
