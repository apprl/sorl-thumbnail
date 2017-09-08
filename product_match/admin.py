from django.contrib import admin
from product_match.models import UrlDetail, UrlVendorSpecificParams


# Register your models here.

class UrlDetailAdmin(admin.ModelAdmin):
    ordering = ('-created',)
    readonly_fields = ('created', 'modified')
    list_display = ('domain', 'path', 'query', 'fragment', 'parameters')
    list_filter = ('domain', 'path')
    raw_id_fields = ('product',)


admin.site.register(UrlDetail, UrlDetailAdmin)


class UrlVendorSpecificParamsAdmin(admin.ModelAdmin):
    pass


admin.site.register(UrlVendorSpecificParams, UrlVendorSpecificParamsAdmin)
