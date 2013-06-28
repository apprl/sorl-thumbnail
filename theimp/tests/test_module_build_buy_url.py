from django.test import TestCase
from django.db.models.loading import get_model

from theimp.parser.modules.build_buy_url import BuildBuyURL


class BuildBuyURLTest(TestCase):
    fixtures = ['initial.json']

    def setUp(self):
        self.vendor = get_model('theimp', 'Vendor').objects.create(name='TestVendor')
        self.mapping_aan = get_model('theimp', 'AffiliateMapping').objects.create(vendor=self.vendor, identifier='test_vendor')

        self.module = BuildBuyURL(None)

    def test_build_buy_url(self):
        parsed_item = self.module({}, {}, 0)
        self.assertEqual(parsed_item, {})

        parsed_item = self.module({'buy_url': 'http://domain.com/buy_url/'}, {}, 0)
        self.assertEqual(parsed_item.get('buy_url'), 'http://domain.com/buy_url/')

    def test_only_url_parameter(self):
        parsed_item = self.module({'url': 'http://domain.com/normal_url/'}, {}, 0)
        self.assertEqual(parsed_item, {})

    def test_affiliate_aan(self):
        parsed_item = self.module({'affiliate': 'aan', 'vendor': 'TestVendor', 'url': 'http://domain.com/normal_url/'}, {}, self.vendor)
        self.assertEqual(parsed_item.get('buy_url'), 'http://apprl.com/a/link/?store_id=test_vendor&url=http%3A%2F%2Fdomain.com%2Fnormal_url%2F')

    def test_affiliate_zanox(self):
        # TODO
        parsed_item = self.module({'affiliate': 'zanox', 'vendor': 'TestVendor', 'url': 'http://domain.com/normal_url/'}, {}, self.vendor)
        self.assertEqual(parsed_item.get('buy_url'), '')

    def test_affiliate_tradedoubler(self):
        # TODO
        parsed_item = self.module({'affiliate': 'tradedoubler', 'vendor': 'TestVendor', 'url': 'http://domain.com/normal_url/'}, {}, self.vendor)
        self.assertEqual(parsed_item.get('buy_url'), '')

    def test_affiliate_linkshare(self):
        # TODO
        parsed_item = self.module({'affiliate': 'linkshare', 'vendor': 'TestVendor', 'url': 'http://domain.com/normal_url/'}, {}, self.vendor)
        self.assertEqual(parsed_item.get('buy_url'), '')

    def test_affiliate_cj(self):
        # TODO
        parsed_item = self.module({'affiliate': 'cj', 'vendor': 'TestVendor', 'url': 'http://domain.com/normal_url/'}, {}, self.vendor)
        self.assertEqual(parsed_item.get('buy_url'), '')

    def test_affiliate_affiliatewindow(self):
        # TODO
        parsed_item = self.module({'affiliate': 'affiliatewindow', 'vendor': 'TestVendor', 'url': 'http://domain.com/normal_url/'}, {}, self.vendor)
        self.assertEqual(parsed_item.get('buy_url'), '')
