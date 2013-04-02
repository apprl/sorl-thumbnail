from django.http import HttpResponseRedirect
from django.contrib import admin
from django.core import urlresolvers

from affiliate.models import Store, Transaction


class StoreAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'user')

admin.site.register(Store, StoreAdmin)


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('store_id', 'order_value', 'cookie_date', 'created', 'modified', 'status')
    list_filter = ('status', 'store_id')

admin.site.register(Transaction, TransactionAdmin)
