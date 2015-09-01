from django.core import urlresolvers
from django.contrib import admin

from apparelrow.statistics.models import ProductClick, ProductStat, NotificationEmailStats, ActiveUser


class ActiveUserAdmin(admin.ModelAdmin):
    list_display = ('period_type', 'period_key', 'period_value')
    list_filter = ('period_type',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(ActiveUser, ActiveUserAdmin)


class ProductClickAdmin(admin.ModelAdmin):
    list_display = ('product', 'click_count', 'link')
    raw_id_fields = ('product',)
    search_fields = ['product__product_name']

    def link(self, product_click):
        url = urlresolvers.reverse('admin:apparel_product_change', args=(product_click.product.id,))
        return '<a href="%s">%s</a>' % (url, url)
    link.short_description = 'Admin link'
    link.allow_tags = True

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(ProductClick, ProductClickAdmin)


class ProductStatAdmin(admin.ModelAdmin):
    list_display = ('action', 'user_id', 'page', 'product', 'vendor', 'price', 'created', 'ip', 'valid')
    list_filter = ('action', 'page', 'created', 'vendor')

    def has_add_permission(self, request):
        return False

admin.site.register(ProductStat, ProductStatAdmin)


class NotificationEmailStatsAdmin(admin.ModelAdmin):
    list_display = ('notification_name', 'notification_count')

admin.site.register(NotificationEmailStats, NotificationEmailStatsAdmin)
