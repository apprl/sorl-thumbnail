from django.contrib import admin

from dashboard.models import Sale

class SaleAdmin(admin.ModelAdmin):
    list_display = ('affiliate', 'vendor', 'status', 'user_id', 'placement', 'commission', 'currency', 'sale_date')
    list_filter = ('affiliate', 'vendor', 'status', 'placement')
    raw_id_fields = ('product',)

admin.site.register(Sale, SaleAdmin)
