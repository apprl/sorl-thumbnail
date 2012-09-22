from django.conf.urls import patterns

urlpatterns = patterns('',
    (r'^$', 'apparelrow.statistics.views.product_click_count'),
)
