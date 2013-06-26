from django.http import HttpResponseRedirect
from django.contrib import admin
from django.core import urlresolvers

from advertiser.models import Store, StoreHistory, Product, Transaction, Cookie

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
    list_display = ('pk', 'store_id', 'order_value', 'cookie_date', 'created', 'modified', 'status', 'automatic_accept')
    list_filter = ('status', 'store_id')
    inlines = (ProductInline,)

admin.site.register(Transaction, TransactionAdmin)


class CookieAdmin(admin.ModelAdmin):
    list_display = ('cookie_id', 'store_id', 'old_cookie_id', 'custom', 'created')
    list_filter = ('store_id',)

admin.site.register(Cookie, CookieAdmin)
