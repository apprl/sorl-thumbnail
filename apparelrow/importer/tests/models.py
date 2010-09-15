import time
from datetime import datetime

from django.test import TestCase, TransactionTestCase

from importer.models import *
from apparel import models as apparel


class ImportLogTest(TestCase):
    def setUp(self):
        self.feed = VendorFeed.objects.create(
            vendor=apparel.Vendor.objects.create(name='My Vendor'),
            url='http://example.com/feed.xml',
            provider_class='DummyProvider',
        )

    def test_defaults(self):
        log = ImportLog.objects.create(vendor_feed=self.feed)
        
        self.assertEqual(log.status, u'running', 'Status is running by default')
        self.assertEqual(log.end_time, None, 'No end_time set')
        self.assertEqual(self.feed.import_log.count(), 1, 'Added to VendorFeed')
        self.assertAlmostEqual(
            time.mktime(log.start_time.timetuple()), 
            time.mktime(datetime.now().timetuple()),
            0, 
            'start_time automatically set to now()'
        )
    
    def test_mark_complete(self):
        log = ImportLog.objects.create(vendor_feed=self.feed)
        
        log.status = 'completed'
        log.save()
        
        self.assertTrue(
            isinstance(log.end_time, datetime),
            'end_time updated if status set to complete'
        )
    
    def test_mark_failure(self):
        log = ImportLog.objects.create(vendor_feed=self.feed)
        log.status = 'failed'
        log.save()
        
        self.assertTrue(
            isinstance(log.end_time, datetime), 
            'end_time updated if status set to failure'
        )

    def test_messages(self):
        log = ImportLog.objects.create(vendor_feed=self.feed)
        log.messages.create(message='Test 1')
        
        self.assertEquals(log.messages.count(), 1, 'Added one import log message')
        self.assertEquals(log.messages.all()[0].status, 'info', 'ImportLogMessage status defaults to info')
        self.assertTrue(isinstance(log.messages.all()[0].datetime, datetime), 'ImportLogMessage datetime set to now')
    
    
class VendorFeedTest(TestCase):
    def setUp(self):
        pass
    
    def test_import_log(self):
        feed = VendorFeed.objects.create(
            vendor=apparel.Vendor.objects.create(name='Vendor'),
            url='http://example.com/feed.xml',
            provider_class='DummyProvider',
        )
        
        log = feed.import_log.create()
        self.assertEquals(feed, log.vendor_feed, 'Relationship OK')
        self.assertEquals(feed.import_log.count(), 1, 'Added ImportLog')
    
if __name__ == '__main__':
    unittest.main()

