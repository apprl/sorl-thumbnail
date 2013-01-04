from django.contrib import admin

from dashboard.models import Sale, Cut, Group

class SaleAdmin(admin.ModelAdmin):
    list_display = ('affiliate', 'vendor', 'status', 'user_id', 'placement', 'commission', 'currency', 'sale_date', 'adjusted')
    list_filter = ('affiliate', 'vendor', 'status', 'placement')
    raw_id_fields = ('product',)

admin.site.register(Sale, SaleAdmin)


class CutAdmin(admin.ModelAdmin):
    list_display = ('group', 'vendor', 'cut')
    list_filter = ('group',)

admin.site.register(Cut, CutAdmin)

admin.site.register(Group)
