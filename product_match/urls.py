from django.conf.urls import  url
from product_match.views import create_short_links_and_lookup_product

url(r'^backend/product/lookup/match/product/$', create_short_links_and_lookup_product,
    name='backend-product-lookup-match-product')
