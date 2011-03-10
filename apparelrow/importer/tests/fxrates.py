import os
from decimal import Decimal

from django.test import TestCase, TransactionTestCase
from django.conf import settings

from importer.fxrates import FXRateImporter
from importer.models import FXRate

class FXRateImporterTest(TestCase):
    def setUp(self):
        pass
    
    def tearDown(self):
        pass
    
    def test_settings(self):
        
        self.assertTrue(settings.APPAREL_BASE_CURRENCY)
        self.assertTrue(settings.APPAREL_FXRATES_URL)
    
    def test_import_new_fxrate(self):
        importer = FXRateImporter()
        
        self.assertTrue(importer.import_fx_rate('USD', 6.38), 'Imported FX Rate')
        
        fxrate = FXRate.objects.filter(
            base_currency=settings.APPAREL_BASE_CURRENCY, 
            currency='USD'
        )
        
        self.assertEquals(len(fxrate), 1)
        self.assertEqual(fxrate[0].currency, 'USD')
        self.assertEqual(fxrate[0].base_currency, settings.APPAREL_BASE_CURRENCY)
        self.assertEqual(fxrate[0].rate, Decimal('6.38'))
        
    def test_import_existing_fxrate(self):
        importer = FXRateImporter()
        
        self.assertTrue(importer.import_fx_rate('USD', 6.38),   'Imported FX Rate')
        self.assertTrue(importer.import_fx_rate('USD', '6.58'), 'Imported FX Rate again')
        
        fxrate = FXRate.objects.filter(
            base_currency=settings.APPAREL_BASE_CURRENCY, 
            currency='USD'
        )
        self.assertEqual(len(fxrate), 1)
        self.assertEqual(fxrate[0].currency, 'USD')
        self.assertEqual(fxrate[0].base_currency, settings.APPAREL_BASE_CURRENCY)
        self.assertEqual(fxrate[0].rate, Decimal('6.58'))
    
    def test_parse_fxrate_file(self):
        sample_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fxrates-samples.rss')
        importer = FXRateImporter()
        
        self.assertTrue(importer.import_feed(sample_file))
        self.assertEqual(   
            [
                (u'AED', Decimal('0.576030'), settings.APPAREL_BASE_CURRENCY), 
                (u'ARS', Decimal('0.631380'), settings.APPAREL_BASE_CURRENCY), 
                (u'EUR', Decimal('0.113460'), settings.APPAREL_BASE_CURRENCY), 
                (u'GBP', Decimal('0.097210'), settings.APPAREL_BASE_CURRENCY)
            ],
            list(FXRate.objects.order_by('currency').values_list('currency', 'rate', 'base_currency'))
        )
        

class FXRateModelTest(TestCase):
    
    def test_model_defaults(self):
        fxrate = FXRate(
            currency='BRL',
            base_currency='SEK',
            rate=0.259767159
        )
        
        self.assertEqual(
            u'%s' % fxrate,
            u'1 SEK in BRL = 0.259767'
        )
