from django.http import HttpResponseRedirect
from django.contrib import admin
from django.conf import settings

from apparelrow.dashboard.models import Sale, Payment, Cut, Group, Signup, StoreCommission, UserEarning, ClickCost, AggregatedData
from apparelrow.dashboard.forms import CutAdminForm, SaleAdminFormCustom


class SaleAdmin(admin.ModelAdmin):
    form = SaleAdminFormCustom
    list_display = ('id', 'original_sale_id', 'affiliate', 'vendor', 'status', 'user_id', 'product_id', 'placement', 'cut', 'commission', 'currency', 'sale_date', 'adjusted', 'paid')
    list_filter = ('affiliate', 'vendor', 'status', 'placement', 'sale_date')
    readonly_fields = ('original_sale_id', 'affiliate', 'paid', 'modified', 'created')
    raw_id_fields = ('referral_user',)

    def save_model(self, request, obj, form, change):
        if obj.is_promo and not change:
            obj.affiliate = 'referral_promo'
            obj.original_sale_id = 'referral_promo_%s' % (obj.user_id,)
            obj.is_referral_sale = False
            obj.exchange_rate = '1'
            obj.converted_amount = settings.APPAREL_DASHBOARD_INITIAL_PROMO_COMMISSION
            obj.converted_commission = settings.APPAREL_DASHBOARD_INITIAL_PROMO_COMMISSION
            obj.amount = settings.APPAREL_DASHBOARD_INITIAL_PROMO_COMMISSION
            obj.commission = settings.APPAREL_DASHBOARD_INITIAL_PROMO_COMMISSION
            obj.original_amount = settings.APPAREL_DASHBOARD_INITIAL_PROMO_COMMISSION
            obj.original_commission = settings.APPAREL_DASHBOARD_INITIAL_PROMO_COMMISSION
            obj.currency = 'EUR'
            obj.original_currency = 'EUR'
            obj.status = Sale.CONFIRMED

        super(SaleAdmin, self).save_model(request, obj, form, change)

admin.site.register(Sale, SaleAdmin)

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('custom_user', 'amount', 'currency', 'paid', 'cancelled', 'modified', 'created')
    list_filter = ('paid', 'cancelled')
    raw_id_fields = ('user',)
    readonly_fields = ('details', 'user', 'amount', 'currency', 'paid', 'cancelled', 'modified', 'created', 'earnings')
    actions = ('mark_as_paid',)

    #def user_link(self, obj):
        #change_url = urlresolvers.reverse('admin:auth_user_change', args=(obj.user.id,))
        #return '<a href="%s">%s</a>' % (change_url, obj.user)
    #user_link.short_description = 'User'
    #user_link.allow_tags = True

    def mark_as_paid(self, request, queryset):
        for payment in queryset.filter(cancelled=False):
            UserEarning.objects.filter(user=payment.user, paid=Sale.PAID_READY).update(paid=Sale.PAID_COMPLETE)
            payment.paid = True
            payment.save()

        return HttpResponseRedirect(request.get_full_path())

    mark_as_paid.short_description = 'Mark payment as paid'

    def custom_user(self, obj):
        return u'%s' % (obj.user.display_name,)

admin.site.register(Payment, PaymentAdmin)

from django.contrib import messages
class CutAdmin(admin.ModelAdmin):
    form = CutAdminForm
    list_display = ('group', 'vendor', 'cut')
    list_filter = ('group',)

    def save_model(self, request, obj, form, change):
        if obj.group.has_cpc_all_stores and obj.vendor.is_cpc and obj.cut != 0.0:
            messages.warning(request, "Vendor is already set as pay per click and publishers are being paid "
                                      "per click for all stores separately. If cut is not 0.00, it may imply the "
                                      "creation of double earnings for these publishers.")
        obj.save()

admin.site.register(Cut, CutAdmin)


class GroupAdmin(admin.ModelAdmin):
    exclude = ('owner', 'owner_cut', 'is_subscriber')

admin.site.register(Group, GroupAdmin)

class SignupAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'blog', 'traffic', 'store', 'referral_user', 'created')
    raw_id_fields = ('referral_user',)

admin.site.register(Signup, SignupAdmin)


class StoreCommissionAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'commission', 'link')

admin.site.register(StoreCommission, StoreCommissionAdmin)


class UserEarningAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'user_earning_type', 'from_product', 'from_user', 'amount', 'date', 'status', 'paid')
    search_fields = ('user__name', 'user_earning_type', 'status', 'paid')

admin.site.register(UserEarning, UserEarningAdmin)

class ClickCostAdmin(admin.ModelAdmin):
    list_display = ('vendor',   'amount', 'currency')

admin.site.register(ClickCost, ClickCostAdmin)

class AggregatedDataAdmin(admin.ModelAdmin):
    list_display = ('id', 'data_type', 'created', 'user_id', 'user_name', 'user_username', 'sale_earnings', 'click_earnings',
                    'sale_plus_click_earnings', 'referral_earnings', 'network_sale_earnings', 'network_click_earnings',
                    'total_network_earnings', 'aggregated_from_id', 'aggregated_from_name', 'aggregated_from_slug',
                    'aggregated_from_image', 'aggregated_from_link',
                    'sales', 'network_sales', 'referral_sales', 'paid_clicks', 'total_clicks')
    search_fields = ('id', 'user_id', 'user_name', 'user_username')
    list_filter = ('data_type', )
admin.site.register(AggregatedData, AggregatedDataAdmin)