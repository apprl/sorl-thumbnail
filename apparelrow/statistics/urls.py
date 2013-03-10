from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'$', 'apparelrow.statistics.views.product_click_count', name='product-click-count'),
)
