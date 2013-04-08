from django.http import HttpResponseRedirect
from django.contrib import admin
from django.core import urlresolvers

from affiliate.models import Store, StoreHistory, Product, Transaction

class StoreHistoryInline(admin.TabularInline):
    model = StoreHistory
    readonly_fields = ('balance', 'created')
    max_num = 1
    extra = 0
    can_delete = False

class StoreAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'user')
    inlines = (StoreHistoryInline,)

admin.site.register(Store, StoreAdmin)


class ProductInline(admin.StackedInline):
    model = Product
    max_num = 1
    extra = 0


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('pk', 'store_id', 'order_value', 'cookie_date', 'created', 'modified', 'status')
    list_filter = ('status', 'store_id')
    inlines = (ProductInline,)

admin.site.register(Transaction, TransactionAdmin)
