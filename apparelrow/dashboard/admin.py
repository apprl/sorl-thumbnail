from django.http import HttpResponseRedirect
from django.contrib import admin
from django.core import urlresolvers

from apparelrow.dashboard.models import Sale, Payment, Cut, Group, Signup, StoreCommission, UserEarning
from apparelrow.dashboard.forms import CutAdminForm

class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_sale_id', 'affiliate', 'vendor', 'status', 'user_id', 'product_id', 'placement', 'cut', 'commission', 'currency', 'sale_date', 'adjusted', 'paid')
    list_filter = ('affiliate', 'vendor', 'status', 'placement', 'sale_date')
    readonly_fields = ('original_sale_id', 'affiliate', 'paid', 'modified', 'created')
    raw_id_fields = ('referral_user',)

admin.site.register(Sale, SaleAdmin)

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('custom_user', 'amount', 'currency', 'paid', 'cancelled', 'modified', 'created')
    list_filter = ('paid', 'cancelled')
    raw_id_fields = ('user',)
    readonly_fields = ('details', 'user', 'amount', 'currency', 'paid', 'cancelled', 'modified', 'created')
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

class CutAdmin(admin.ModelAdmin):
    form = CutAdminForm
    list_display = ('group', 'vendor', 'cut')
    list_filter = ('group',)

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
    list_display = ('id',   'user', 'user_earning_type', 'from_product', 'from_user', 'amount', 'date', 'status', 'paid')
    search_fields = ('user__name', 'user_earning_type', 'status', 'paid')

admin.site.register(UserEarning, UserEarningAdmin)
