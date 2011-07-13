from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^$', 'apparelrow.statistics.views.product_click_count'),
)
