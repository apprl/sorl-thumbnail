import os, datetime

from django.test import TestCase, TransactionTestCase
from django.conf import settings

from importer.framework.provider import Provider, load_provider, CSVProvider
from importer.framework.mapper   import DataMapper
from importer.models import VendorFeed
from apparel import models as apparel



# - Dummy Classes -


class MyCSVProvider(CSVProvider):
    def __init__(self, *args, **kwargs):
        super(MyCSVProvider, self).__init__(*args, **kwargs)
        self.fieldnames = (
            'myfield1', 'myfield2', 'myfield3', 'myfield4', 'myfield5',
            'myfield6', 'myfield7', 'myfield8', 'myfield9', 'myfield10',
        )
        self.imported_data = []     # For testing only. All parsed and mapped data ends up here
    
    def import_data(self, data):
        self.imported_data.append(data)

class MyMapper(DataMapper):
    """
    This is a dummy mapper that just returns whatever it's been given to process
    """
    def translate(self):
        return self.record


# - Actual Test Cases -


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
            os.remove(self._dummy_path)
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


class CSVProviderTest(TestCase):
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
            os.remove(self._dummy_path)
        except OSError:
            pass
    
    def test_csv_class(self):
        p = MyCSVProvider(self.feed)
        
        self.assertEquals(p.extension, 'csv', 'Extension defaults to CSV')
        self.assertEquals(p.dialect, None, 'There is a dialect property')
    
    def test_csv_parsing(self):
        p = MyCSVProvider(self.feed)
        p.mapper = MyMapper
        
        # FIXME: Why isn't there an inverse assertRaises?
        try:
            p.run(from_warehouse=True, for_date=self.test_date)
        except Exception, e:
            print e
            self.fail('Parse CSV file')
        else:
            self.assertTrue(True, 'Parsed and imported CSV file')
                
        self.assertEquals(
            p.imported_data,
            [{'myfield1': u'one',
             'myfield10': u'ten',
             'myfield2': u'two',
             'myfield3': u'three',
             'myfield4': u'four',
             'myfield5': u'five',
             'myfield6': u'six',
             'myfield7': u'seven',
             'myfield8': u'eight',
             'myfield9': u'nine'}],
            'Parsed data given to mapper'
        )
        
    




