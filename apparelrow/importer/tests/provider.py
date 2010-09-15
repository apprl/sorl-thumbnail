import os, datetime

from django.test import TestCase, TransactionTestCase
from django.conf import settings

from importer.framework.provider import Provider, load_provider
from importer.models import VendorFeed
from apparel import models as apparel



class ProviderBaseTest(TestCase):
    """
    Tests basic functionality of the Provider class
    """
    def setUp(self):
        self.feed = VendorFeed.objects.create(
            vendor=apparel.Vendor.objects.create(name='My Vendor'),
            url='http://example.com/feed.csv',
            username='the username',
            password='the password',
            provider_class='DummyProvider',
        )
        self.test_date = datetime.date(2010, 9, 15)
        self._dummy_path = os.path.join(settings.APPAREL_IMPORTER_WAREHOUSE, 'my_vendor', '%s.csv' % self.test_date.strftime('%Y-%m-%d'))
        
        if not os.path.exists(os.path.split(self._dummy_path)[0]):
            os.makedirs(os.path.split(self._dummy_path)[0])
        
        # Write a dummy file to disk
        fh = open(self._dummy_path,'w')
        fh.write('one,two,three,four,five,six,seven,eight,nine,ten\n')
        fh.close()
    
    def tearDown(self):
        try:
            pass
            # os.remove(self._dummy_path)
        except OSError:
            pass
        
    def test_create(self):
        p = Provider(self.feed)
        
        self.assertEquals(p.username, 'the username', 'Username set from feed')
        self.assertEquals(p.password, 'the password', 'password set from feed')
        self.assertEquals(p.url,      'http://example.com/feed.csv', 'URL set from feed')
        self.assertEquals(p.feed, self.feed, 'Reference to VendorFeed')
        self.assertEquals(p.file, None, 'file defaults to None')
        self.assertEquals(p.name, 'my_vendor', 'name constructed from vendor')
        self.assertEquals(p.extension, None, 'extension defaults to None')
        
        self.assertRaises(Exception, p.run)

    def test_load_provider(self):
        p = load_provider('sample', self.feed)
        
        self.assertTrue(isinstance(p, Provider), 'Provider extends Provider')
    
    
    def test_fetch_warehouse(self):
        p = load_provider('sample', self.feed)
        p.fetch(from_warehouse=True, for_date=self.test_date)
        
        self.assertTrue(os.path.exists(self._dummy_path), 'Warehouse directory created when needed')
        self.assertTrue(isinstance(p.file, file), 'File object assiged to Proivider')
        self.assertTrue(p.file.closed is False, 'File object is opened')
        self.assertEqual(p.file.mode, 'r', 'File object is opened for reading')
    
