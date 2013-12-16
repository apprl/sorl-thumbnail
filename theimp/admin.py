from django.contrib import admin
from django.db.models.loading import get_model


class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'affiliate_identifier', 'comment', 'is_active', 'created', 'modified')
    list_filter = ('is_active',)
    readonly_fields = ('name', 'created', 'modified')


class ProductAdmin(admin.ModelAdmin):
    list_display = ('key', 'vendor', 'is_auto_validated', 'is_manual_validated', 'created', 'modified')
    list_filter = ('is_auto_validated', 'is_manual_validated', 'dropped', 'vendor')
    readonly_fields = ('key', 'is_auto_validated', 'created', 'modified', 'vendor', 'dropped')
    search_fields = ('key',)


class BrandMappingAdmin(admin.ModelAdmin):
    list_display = ('brand', 'vendor', 'mapped_brand')
    readonly_fields = ('vendor', 'brand', 'created', 'modified')


class CategoryMappingAdmin(admin.ModelAdmin):
    list_display = ('category', 'vendor', 'mapped_category')
    readonly_fields = ('vendor', 'category', 'created', 'modified')


admin.site.register(get_model('theimp', 'Vendor'), VendorAdmin)
admin.site.register(get_model('theimp', 'Product'), ProductAdmin)
admin.site.register(get_model('theimp', 'BrandMapping'), BrandMappingAdmin)
admin.site.register(get_model('theimp', 'CategoryMapping'), CategoryMappingAdmin)
admin.site.register(get_model('theimp', 'Mapping'))
