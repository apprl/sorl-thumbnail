from django.http import HttpResponseRedirect
from django.contrib import admin
from django.core import urlresolvers

from apparelrow.dashboard.models import Sale, Payment, Cut, Group, Signup, StoreCommission

class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'affiliate', 'vendor', 'status', 'user_id', 'product_id', 'placement', 'cut', 'commission', 'currency', 'sale_date', 'adjusted', 'paid')
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
            Sale.objects.filter(user_id=payment.user.pk, paid=Sale.PAID_READY).update(paid=Sale.PAID_COMPLETE)
            payment.paid = True
            payment.save()

        return HttpResponseRedirect(request.get_full_path())

    mark_as_paid.short_description = 'Mark payment as paid'

    def custom_user(self, obj):
        return u'%s' % (obj.user.display_name,)

admin.site.register(Payment, PaymentAdmin)

class CutAdmin(admin.ModelAdmin):
    list_display = ('group', 'vendor', 'cut')
    list_filter = ('group',)

admin.site.register(Cut, CutAdmin)

admin.site.register(Group)

class SignupAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'blog', 'store', 'referral_user', 'created')
    raw_id_fields = ('referral_user',)

admin.site.register(Signup, SignupAdmin)


class StoreCommissionAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'commission', 'link')

admin.site.register(StoreCommission, StoreCommissionAdmin)
