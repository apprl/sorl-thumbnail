from django.core import urlresolvers
from django.contrib import admin

from statistics.models import ProductClick

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
