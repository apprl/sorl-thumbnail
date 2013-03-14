import time
from datetime import datetime

from django.test import TestCase, TransactionTestCase

from apparelrow.importer.models import *
from apparelrow.apparel import models as apparel


class ImportLogTest(TestCase):
    def setUp(self):
        self.feed = VendorFeed.objects.create(
            name='myvendor',
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
            name='myvendor',
            vendor=apparel.Vendor.objects.create(name='Vendor'),
            url='http://example.com/feed.xml',
            provider_class='DummyProvider',
        )
        
        log = feed.import_log.create()
        self.assertEquals(feed, log.vendor_feed, 'Relationship OK')
        self.assertEquals(feed.import_log.count(), 1, 'Added ImportLog')
    
    def test_lastest_log(self):
        feed1 = VendorFeed.objects.create(
            name='vendor1',
            vendor=apparel.Vendor.objects.create(name='Vendor 1'),
            url='http://example.com/feed.xml',
            provider_class='DummyProvider',
        )
        feed2 = VendorFeed.objects.create(
            name='vendor2',
            vendor=apparel.Vendor.objects.create(name='Vendor 2'),
            url='http://example.com/feed.xml',
            provider_class='DummyProvider',
        )
        
        self.assertEquals(feed1.latest_import_log, None, 'No import logs available')
        
        log1 = feed1.import_log.create()
        self.assertEquals(feed1.latest_import_log, log1, 'Returns lastest log object')
        time.sleep(1)
        log2 = feed1.import_log.create()
        self.assertEquals(feed1.import_log.count(), 2, 'Two logs associated with feed')
        self.assertEquals(feed1.latest_import_log, log2, 'Only the latest returned by latest_log accessor')
        
        time.sleep(1)
        log3 = feed2.import_log.create()
        self.assertEquals(feed1.latest_import_log, log2, "Feed1's import log unchanged")
        self.assertEquals(feed2.latest_import_log, log3, "Feed2's import log correct")
        
        
    
if __name__ == '__main__':
    unittest.main()

