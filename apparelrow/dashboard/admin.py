from django.contrib import admin

from dashboard.models import Sale

class SaleAdmin(admin.ModelAdmin):
    list_filter = ('affiliate', 'vendor', 'status', 'placement')
    raw_id_fields = ('product',)

admin.site.register(Sale, SaleAdmin)
