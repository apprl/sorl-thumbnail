from django.conf.urls import url

url(r'^backend/product/lookup/$', 'apparelrow.apparel.views.lookup_product', name='product-lookup'),
