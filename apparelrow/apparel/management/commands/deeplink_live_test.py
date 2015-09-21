__author__ = 'apprl'

from django.db.models.loading import get_model
from django.contrib.auth import get_user_model
from django.test.client import RequestFactory
from django.core.management.base import BaseCommand
from apparelrow.apparel.views import product_lookup
from urlparse import urlparse, parse_qs
from django.http.response import Http404
from django.contrib.sites.models import Site
import random
import logging
import requests
import json

logger = logging.getLogger('live_test')

class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        logger.info('Initiating Live Test')

        logger.info('Testing Short Links for Products...')
        vendor_product = get_model('apparel', 'VendorProduct')
        product = get_model('apparel', 'Product')
        products = product.objects.filter(published=True, availability=True)
        last = products.count() - 1
        try:
            indexes = random.sample(range(0, last), 10)
            rf = RequestFactory()
            try:
                get_user_model().objects.get(username='test_apprl').delete()
            except get_user_model().DoesNotExist:
                pass

            user = get_user_model().objects.create_user(username='test_apprl', password='test_apprl', is_partner=True,
                                                        partner_group=get_model('dashboard', 'Group').objects.all()[0],)
            response = rf.post('/login/', {'username': user.username, 'password': user.password})

            for key in indexes:
                instance = products[key]
                logger.info('Creating DeepLink for product %s' % (instance.product_name))
                vp = vendor_product.objects.filter(product=instance)
                if len(vp) > 0:
                    # Test lookup for Chrome Extension from the BuyURL attribute
                    current_site = Site.objects.get_current()
                    try:
                        request = requests.get(vp[0].buy_url)
                        hostname = urlparse(request.url).hostname
                        url = '/backend/product/lookup/?key=%s&domain=%s' % (request.url, hostname)
                        lookup_request = rf.get(url)
                        lookup_request.user = user
                        response = product_lookup(lookup_request)
                        json_data = json.loads(response.content)

                        if 'product_short_link' in json_data:
                            try:
                                ''' ShortProductLink was created, check that this ShortProductLink actually corresponds
                                to the right product link
                                '''
                                link_key = json_data['product_short_link'].rsplit('/', 2)[1]
                                short_link_instance = get_model('apparel', 'ShortProductLink').\
                                    objects.get_for_short_link(link_key)
                                if short_link_instance.product == instance and short_link_instance.user == user:
                                    logger.info('ShortProductLink for Product %s and user %s was created successfully' %
                                                (instance.product_name, user.name))
                                else:
                                    logger.warn('ShortProductLink for Product %s and user %s was not created successfully' %
                                                (instance.product_name, user.name))
                            except get_model('apparel', 'ShortProductLink').DoesNotExist:
                                ''' ShortDomainLink was created, this should not happen as we are doing a lookup
                                for products that exist and are available in our database
                                '''
                                logger.warn('No Short link was created for product %s, user %s and vendor %s'
                                            % (instance.product_name, user, vp[0]))
                                logger.info('Domain Link was created instead for %s, user %s and vendor %s'
                                            % (instance.product_name, user, vp[0]))
                                link_key = json_data['product_short_link'].rsplit('/', 2)[1]
                                url, vendor_name, user_id = get_model('apparel', 'ShortDomainLink').\
                                    objects.get_short_domain_for_link(link_key)
                                if not user_id == user.id or not vendor_name == vp[0].vendor.name:
                                    logger.warn('Short link is not correct for user %s and vendor %s' % (user, vp[0]))
                        else:
                            ''' No DeepLink was created, log a warning message instead
                            '''
                            logger.warn('No deep link was created for user %s and product %s from vendor %s'
                                        % (user, instance.product_name, vp[0]))
                    except Http404:
                        logger.warn('Raised 404 error for url %s, user %s and product %s'
                                    % (url, user, instance.product_name))
                    except requests.ConnectionError, e:
                            logger.warn('Connection error for url %s : %s'
                                        % (vp[0].buy_url, e.message))
        except ValueError:
            logger.warn('Amount of indexes are larger than VendorProduct table size')

        # Test Deep Domain Link
        logger.info('Testing Domain Deep Links...')
        urls_pool = (
            'http://www.aldoshoes.com/international',
            'http://altewaisaome.com/',
            'http://www.asos.com/women/',
            'http://www.boozt.com/se/sv/klader-for-man',
            'http://www.boozt.com/no/no/menn?group=external',
            'http://www.carinwester.com/',
            'http://confidentliving.se/',
            'http://www.houseofdagmar.se/',
            'http://eleven.se/',
            'http://elevenfiftynine.se/',
            'http://www.filippa-k.com/se',
            'http://www.gramshoes.com/',
            'http://www.jc.se/',
            'http://www.laurenbbeauty.com/',
            'http://www.luisaviaroma.com/',
            'http://www.menlook.com/',
            'http://www.minimarket.se/',
            'http://www.monicavinader.com/',
            'http://www.mq.se/',
            'http://www.mrporter.com/',
            'http://nelly.com/se/kl%C3%A4der-f%C3%B6r-kvinnor',
            'http://www.net-a-porter.com/',
            'http://www.oki-ni.com/',
            'http://www.philipb.com/',
            'http://www.room21.no/',
            'http://www.rum21.se/',
            'https://shirtonomy.se/',
            'https://www.ssense.com/',
            'https://www.theoutnet.com/en-SE/',
            'http://www.vrients.com/',
            'https://www.wolfandbadger.com/uk/'
        )

        for link in urls_pool:
            try:
                request = requests.get(link)
                hostname = urlparse(request.url).hostname
                url = '/backend/product/lookup/?key=%s&domain=%s' % (link, hostname)
                lookup_request = rf.get(url)
                lookup_request.user = user
                response = product_lookup(lookup_request)
                json_data = json.loads(response.content)
                if 'product_short_link' in json_data:
                    link_key = json_data['product_short_link'].rsplit('/', 2)[1]
                    url, vendor_name, user_id = get_model('apparel', 'ShortDomainLink').objects.\
                        get_short_domain_for_link(link_key)
                    parsed_url = urlparse(url)
                    query_array = parse_qs(parsed_url.query)
                    if url in query_array and query_array['url'][0] == link:
                        logger.info("Deep domain link created successfully for %s" % link)
                    else:
                        logger.warn('Deep domain link not created successfully for %s' % link)
                else:
                    logger.warn('No deep link was created for user %s and product %s from vendor %s'
                                % (user, instance.product_name, vp[0]))
            except Http404:
                logger.warn('Raised 404 error for url %s, user %s and product %s' % (url, user, instance.product_name))
            except requests.ConnectionError, e:
                        logger.warn('Connection error for url %s : %s'
                                    % (link, e.message))