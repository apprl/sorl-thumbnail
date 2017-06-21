from django import forms
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.core import urlresolvers
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils.translation import ugettext_lazy as _

from advertiser.models import Store, StoreHistory, StoreInvoice, Product, Transaction, Cookie
from advertiser.utils import calculate_balance, get_unpaid_accepted_transactions

import csv


class StoreHistoryInline(admin.TabularInline):
    model = StoreHistory
    readonly_fields = ('balance', 'created')
    max_num = 1
    extra = 0
    can_delete = False

class StoreAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'user', 'cookie_days')
    inlines = (StoreHistoryInline,)
    raw_id_fields = ('user',)

admin.site.register(Store, StoreAdmin)


class StoreInvoiceAdminForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super(StoreInvoiceAdminForm, self).clean()
        if 'store' in cleaned_data:
            store = cleaned_data['store']
            if not get_unpaid_accepted_transactions(store):
                raise ValidationError('No accepted transactions found that are unpaid.')

        return cleaned_data

def mark_as_paid(modeladmin, request, queryset):
    for invoice in queryset:
        invoice.is_paid = True
        invoice.transactions.update(is_paid=True)
        invoice.save()

        calculate_balance(invoice.store.identifier)

mark_as_paid.short_description = 'Mark selected invoices as paid'


def action_view_transactions(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Store',
        'Created',
        'Invoice id',
        'Order id',
        'Currency',
        'Order Value',
        'Commission',
        'Status'])
    for si in queryset.all():
        for t in si.transactions.all():
            writer.writerow([
                str(t.store_id),
                str(t.invoice_id),
                str(t.created),
                str(t.order_id),
                t.currency,
                str(t.original_order_value),
                str(t.original_commission),
                t.status
            ])
    return HttpResponse(response)

action_view_transactions.short_description = "View Transactions"

class StoreInvoiceAdmin(admin.ModelAdmin):
    form = StoreInvoiceAdminForm
    list_display = ('store', 'created', 'is_paid', 'total', 'count')
    list_filter = ('is_paid', 'store')
    readonly_fields = ('is_paid', 'created', 'modified')
    actions = [mark_as_paid, action_view_transactions]

    def get_readonly_fields(self, request, obj = None):
        if obj:
            return ('store',) + self.readonly_fields

        return self.readonly_fields

    def count(self, store_invoice):
        return store_invoice.transactions.count()
    count.admin_order_field = 'transactions__count'
    count.short_description = 'Transaction Count'

    def total(self, store_invoice):
        total, currency = store_invoice.get_total()
        return '%s %s' % (total, currency)
    total.short_description = 'Transaction Total'


admin.site.register(StoreInvoice, StoreInvoiceAdmin)


class ProductInline(admin.StackedInline):
    model = Product
    max_num = 1
    extra = 0


class ValidListFilter(SimpleListFilter):
    title = _('apprl transaction')
    parameter_name = 'valid'

    def lookups(self, request, model_admin):
        return (
            ('all', _('All')),
            (None, _('yes')),
            ('no', _('no')),
        )

    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == lookup,
                'query_string': cl.get_query_string({
                    self.parameter_name: lookup,
                }, []),
                'display': title,
            }

    def queryset(self, request, queryset):
        if self.value() == 'yes' or self.value() == None:
            return queryset.filter(status__in=[Transaction.ACCEPTED, Transaction.REJECTED, Transaction.PENDING])
        elif self.value() == 'no':
            return queryset.filter(status__in=[Transaction.INVALID, Transaction.TOO_OLD])
        else:
            return queryset


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('pk', 'store_id', 'order_value', 'original_commission', 'original_currency', 'cookie_date', 'created', 'modified', 'status', 'automatic_accept', 'is_paid')
    list_filter = ('status', 'store_id', ValidListFilter)
    inlines = (ProductInline,)
    readonly_fields = ('invoice', 'automatic_accept', 'created', 'modified', 'cookie_date', 'ip_address',
                       'status_date', 'store_id', 'original_currency', 'original_commission', 'original_order_value', 'order_id')

    def get_readonly_fields(self, request, obj = None):
        if obj and obj.invoice and obj.invoice.is_paid:
            return ('commission', 'order_value', 'is_paid', 'status') + self.readonly_fields

        if obj and obj.invoice:
            return self.readonly_fields

        return ()

admin.site.register(Transaction, TransactionAdmin)


class CookieAdmin(admin.ModelAdmin):
    list_display = ('cookie_id', 'store_id', 'old_cookie_id', 'custom', 'created')
    list_filter = ('store_id',)

admin.site.register(Cookie, CookieAdmin)
