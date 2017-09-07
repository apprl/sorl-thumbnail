from django.test import TestCase
import urlparse

# Create your tests her
from model_mommy import mommy

from apparelrow.apparel.tests import _create_dummy_image
from product_match.models import UrlVendorSpecificParams, UrlDetail


def match_urls(ce_url, computed_url, param):
    parsed_url = urlparse.urlparse(ce_url)
    match = False

    if param:
        id = urlparse.parse_qs(parsed_url.query)[param]
        ce_url_computed = parsed_url.scheme + '://' + parsed_url.netloc + parsed_url.path + '?' + param + '=' + id[0]

    else:
        ce_url_computed = parsed_url.scheme + '://' + parsed_url.netloc + parsed_url.path
        if ce_url_computed.endswith('/'):
            ce_url_computed = ce_url_computed.rstrip('/')

    if ce_url_computed == computed_url:
        match = True

    return match


def match_urls_db(ce_url, param):
    parsed_url = urlparse.urlparse(ce_url)
    match = False

    if param:
        id = urlparse.parse_qs(parsed_url.query)[param]
        ce_url_computed = parsed_url.scheme + '://' + parsed_url.netloc + parsed_url.path + '?' + param + '=' + id[0]

    else:
        ce_url_computed = parsed_url.scheme + '://' + parsed_url.netloc + parsed_url.path
        if ce_url_computed.endswith('/'):
            ce_url_computed = ce_url_computed.rstrip('/')

    computed_url = UrlDetail.objects.filter(url=ce_url_computed).values_list('url', flat=True).first()

    if ce_url_computed == computed_url:
        match = True

    return match


class TestLinks(TestCase):
    def test_parameters(self):
        computed_url = 'https://www.mq.se/article/alexia_trousers?attr1_id=1347'  # spider
        ce_url = 'https://www.mq.se/article/alexia_trousers?attr1_id=1347&size=55'
        param = 'attr1_id'
        matched = match_urls(ce_url, computed_url, param)
        assert matched == True

    def test_parameters_asos(self):
        computed_url = 'http://www.asos.com/pulsaderm/pulsaderm-set-of-2-heads-microderm-sponge/prd/5076307'  # spider
        ce_url = 'http://www.asos.com/pulsaderm/pulsaderm-set-of-2-heads-microderm-sponge/prd/5076307/?clr=microdermsponge&SearchQuery=microderm&SearchRedirect=true'
        param = None
        matched = match_urls(ce_url, computed_url, param)
        assert matched == True

    def test_parameters_another_id(self):
        computed_url = 'https://www.mq.se/article/alexia_trousers?id=1347'  # spider
        ce_url = 'https://www.mq.se/article/alexia_trousers?id=1347&size=55'
        param = 'id'
        matched = match_urls(ce_url, computed_url, param)
        assert matched == True

    def test_parameters_another_id(self):
        computed_url = 'https://www.mq.se/article/alexia_trousers?id=1347'  # spider
        ce_url = 'https://www.mq.se/article/alexia_trousers?id=1347&size=55'
        param = 'id'
        matched = match_urls(ce_url, computed_url, param)
        assert matched == True

    def test_parameters_hash(self):
        computed_url = 'http://www.stories.com/gb/Jewellery/Earrings/Pearl_Pendant_Earrings/582808-0509056002.2'  # spider
        ce_url = 'http://www.stories.com/gb/Jewellery/Earrings/Pearl_Pendant_Earrings/582808-0509056002.2#c-24479'
        param = None
        matched = match_urls(ce_url, computed_url, param)
        assert matched == True

    def test_parameters_dbase(self):
        mommy.make(UrlVendorSpecificParams, domain='www.mq.se', param_id_name='attr1_id')

        computed_url = 'https://www.mq.se/article/alexia_trousers?attr1_id=1347'  # spider
        ce_url = 'https://www.mq.se/article/alexia_trousers?attr1_id=1347&size=55'

        domain = get_vendor_domain(ce_url)
        param = get_vendor_params(domain)

        matched = match_urls(ce_url, computed_url, param)
        assert matched == True

    def test_url_dbase(self):
        ce_url = 'https://www.mq.se/article/alexia_trousers?attr1_id=1347&size=55'
        computed_url = 'https://www.mq.se/article/alexia_trousers?attr1_id=1347'  # spider
        product_image = _create_dummy_image()
        mommy.make(UrlVendorSpecificParams, domain='www.mq.se', param_id_name='attr1_id')
        mommy.make(UrlDetail, url=computed_url, product__product_image=product_image)

        domain = get_vendor_domain(ce_url)
        param = get_vendor_params(domain)

        matched = match_urls_db(ce_url, param)
        assert matched == True


def get_domain(url):
    parsed_url = urlparse.urlsplit(url)
    domain = parsed_url.netloc
    return domain


def get_vendor_params(domain):
    param = UrlVendorSpecificParams.objects.filter(domain=domain).values_list('param_id_name', flat=True).first()
    return param
