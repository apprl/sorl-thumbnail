from django.contrib import admin
from product_match.models import UrlDetail


# Register your models here.

class UrlAdmin(admin.ModelAdmin):
    ordering = ('-created',)
    readonly_fields = ('created', 'modified')
    list_display = ('domain', 'path', 'query', 'fragment', 'parameters')
    list_filter = ('domain', 'path')
    raw_id_fields = ('product',)


admin.site.register(UrlDetail, UrlAdmin)
