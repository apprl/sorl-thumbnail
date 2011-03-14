import os
from decimal import Decimal

from django.test import TestCase, TransactionTestCase
from django.conf import settings

from importer.fxrates import FXRateImporter
from importer.models import FXRate
from apparel.models import VendorProduct

class FXRateImporterTest(TestCase):
    def setUp(self):
        self.sample_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fxrates-samples.rss')
    
    def tearDown(self):
        pass
    
    def test_settings(self):
        
        self.assertTrue(settings.APPAREL_BASE_CURRENCY)
        self.assertTrue(settings.APPAREL_FXRATES_URL)
    
    
    def test_import_new_fxrate(self):
        importer = FXRateImporter(
            base_currency=settings.APPAREL_BASE_CURRENCY
        )
        
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
        importer = FXRateImporter(
            base_currency='BRL'
        )
        
        self.assertTrue(importer.import_fx_rate('USD', 6.38),   'Imported FX Rate')
        self.assertTrue(importer.import_fx_rate('USD', '6.58'), 'Imported FX Rate again')
        
        fxrate = FXRate.objects.filter(
            base_currency=importer.base_currency,
            currency='USD'
        )
        self.assertEqual(len(fxrate), 1)
        self.assertEqual(fxrate[0].currency, 'USD')
        self.assertEqual(fxrate[0].base_currency, 'BRL')
        self.assertEqual(fxrate[0].rate, Decimal('6.58'))
    
    def test_parse_fxrate_file(self):
        importer = FXRateImporter(
            base_currency='SEK'
        )
        
        self.assertTrue(importer.import_feed(self.sample_file))
        self.assertEqual(   
            [
                (u'AED', Decimal('0.576030'), u'SEK'), 
                (u'ARS', Decimal('0.631380'), u'SEK'), 
                (u'EUR', Decimal('0.113460'), u'SEK'), 
                (u'GBP', Decimal('0.097210'), u'SEK')
            ],
            list(FXRate.objects.order_by('currency').values_list('currency', 'rate', 'base_currency'))
        )
    
    def test_parse_fxrate_file_run(self):
        importer = FXRateImporter(
            base_currency='SEK',
            file=self.sample_file
        )
        
        self.assertTrue(importer.run())
        self.assertEqual(4, FXRate.objects.count())
        

class FXRateModelTest(TestCase):
    fixtures = ['test-fxrates.yaml']
    
    def test_model_unicode(self):
        self.assertEqual(
            u'%s' % FXRate.objects.get(pk=1),
            u'1 SEK in BRL = 0.259600'
        )
    
    def test_convert_amount(self):
        brl = FXRate.objects.get(pk=1)
        self.assertEqual(Decimal('3852.080123'), brl.convert(1000))
    
    def test_update_prices(self):
        
        self.assertEqual(4, VendorProduct.objects.filter(currency=None).count())
        
        brl = FXRate.objects.get(pk=1)
        brl.update_prices()
        
        self.assertEqual(2, VendorProduct.objects.filter(currency=None).count())
        self.assertEqual(Decimal('3850.00'), VendorProduct.objects.get(pk=1).price)
        self.assertEqual('SEK', VendorProduct.objects.get(pk=1).currency)
        self.assertEqual(Decimal('4235.00'), VendorProduct.objects.get(pk=3).price)
        self.assertEqual('SEK', VendorProduct.objects.get(pk=3).currency)
        
        VendorProduct.objects.filter(pk=1).update(original_price=1050)
        brl.update_prices()
        
        self.assertEqual(2, VendorProduct.objects.filter(currency=None).count())
        self.assertEqual(Decimal('4042.50'), VendorProduct.objects.get(pk=1).price)
        self.assertEqual('SEK', VendorProduct.objects.get(pk=1).currency)
        
