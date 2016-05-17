# -*- coding: utf-8 -*-
from theimp.utils import compare_scraped_and_saved, stringify

__author__ = 'klaswikblad'

from unittest import TestCase
import simplejson

class ImportIfChangedTest(TestCase):

    def setUp(self):
        pass

    def test_compare_scraped_and_saved(self):
        json_scraped = simplejson.loads('{"sku": "(407) Ref: F353014, Col: 1 (+marcella front)", "category": "Skjorta", "vendor": "shirtonomy", "description": "Den perfekta smokingskjortan. Dess krage, br\\u00f6st och franska manschetter \\u00e4r f\\u00f6rst\\u00e4rkta med pik\\u00e9v\\u00e4vt Marcellatyg, vilket lyfter din smokings eleganta framtoning ytterligare. Smokingskjortan kompletteras med tv\\u00e5 l\\u00f6stagbara br\\u00f6stknappar (obs. ing\\u00e5r ej). Smokingskjortans \\u00f6vriga designattribut best\\u00e5r av: White Twill-tyg, Full spread-krage, kantig fransk manschett, Nemo-knappar i p\\u00e4rlemor samt ryggins\\u00f6mnad f\\u00f6r b\\u00e4sta passform.", "regular_price": "1200.00", "url": "http://shirtonomy.se/skjortor/tyg/marcella-tux-shirt/", "gender": "M", "brand": "Shirtonomy", "discount_price": "1200.00", "image_urls": ["https://shirtonomy.se/media/store/img/fabrics/product-62-gxbl_L.jpg"], "currency": "SEK", "colors": "Vit", "affiliate": "aan", "key": "http://shirtonomy.se/skjortor/tyg/marcella-tux-shirt/", "images": [{"url": "https://shirtonomy.se/media/store/img/fabrics/product-62-gxbl_L.jpg", "path": "full/00/00e2000c390bcb3b3667e87dc6e59c794ff4eb6b.jpg", "checksum": "591522690288226f0bbc3efa09a9ab9b"}], "stock": "51", "in_stock": false, "name": "Marcella Tux Shirt"}')
        product_scraped = simplejson.loads('{"sku": "(407) Ref: F353014, Col: 1 (+marcella front)", "category": "Skjorta", "vendor": "shirtonomy", "description": "Den perfekta smokingskjortan. Dess krage, br\\u00f6st och franska manschetter \\u00e4r f\\u00f6rst\\u00e4rkta med pik\\u00e9v\\u00e4vt Marcellatyg, vilket lyfter din smokings eleganta framtoning ytterligare. Smokingskjortan kompletteras med tv\\u00e5 l\\u00f6stagbara br\\u00f6stknappar (obs. ing\\u00e5r ej). Smokingskjortans \\u00f6vriga designattribut best\\u00e5r av: White Twill-tyg, Full spread-krage, kantig fransk manschett, Nemo-knappar i p\\u00e4rlemor samt ryggins\\u00f6mnad f\\u00f6r b\\u00e4sta passform.", "regular_price": "1200.00", "url": "http://shirtonomy.se/skjortor/tyg/marcella-tux-shirt/", "gender": "M", "brand": "Shirtonomy", "discount_price": "1200.00", "image_urls": ["https://shirtonomy.se/media/store/img/fabrics/product-62-gxbl_L.jpg"], "currency": "SEK", "colors": "Vit", "affiliate": "aan", "key": "http://shirtonomy.se/skjortor/tyg/marcella-tux-shirt/", "images": [{"url": "https://shirtonomy.se/media/store/img/fabrics/product-62-gxbl_L.jpg", "path": "full/00/00e2000c390bcb3b3667e87dc6e59c794ff4eb6b.jpg", "checksum": "591522690288226f0bbc3efa09a9ab9b"}], "stock": "50", "in_stock": true, "name": "Marcella Tux Shirt"}')

        fields = compare_scraped_and_saved(json_scraped, product_scraped)
        print fields
        self.assertEquals(fields, [("in_stock", False, True), ("stock", "51", "50")])

    def test_stringify(self):
        self.assertEquals("f\xc3\xb6r", stringify("f\xc3\xb6r"))
        self.assertEquals("f\xc3\xb6r", stringify(u"f\xf6r"))
        self.assertEquals("white,yellow", stringify(("white","yellow")))
        self.assertEquals("white,yellow", stringify(["white","yellow"]))
        self.assertEquals("f\xc3\xa4rger,yellow", stringify([u'f\xe4rger',"yellow"]))
        self.assertEquals("f\xc3\xa4rger,yellow,True", stringify([u'f\xe4rger',"yellow", True]))
        self.assertEquals("f\xc3\xa4rger,yellow,None", stringify([u'f\xe4rger',"yellow", None]))
        print "Passed stringify"
        #json_scraped = simplejson.loads( '{"sku": "(311) Ref: F364844, Col: 13", "category": "Skjorta", "vendor": "shirtonomy", "description": "Himmelsbl\\u00e5 twill tillverkad av 100% egyptisk bomull. Tyget \\u00e4r mycket mjukt och skrynkelt\\u00e5ligt, vilket g\\u00f6r att dess krispiga karakt\\u00e4r bevaras l\\u00e4ngre. Dess fint hundtandsm\\u00f6nstrade v\\u00e4v g\\u00f6r att skjortan uppfattas som enf\\u00e4rgad samtidigt som m\\u00f6nstret ger tyget en levande struktur. L\\u00e5t dina val av krage och manschett styras av hur pass formell framtoning du efterstr\\u00e4var. Tyget tillverkas i Storbritannien.", "regular_price": "900.00", "url": "http://shirtonomy.se/skjortor/tyg/sky-puppy-twill/", "gender": "M", "brand": "Shirtonomy", "discount_price": "900.00", "image_urls": ["https://shirtonomy.se/media/store/img/fabrics/product-65-6vc0_L.jpg"], "currency": "SEK", "colors": "Bl\\u00e5", "affiliate": "aan", "key": "http://shirtonomy.se/skjortor/tyg/sky-puppy-twill/", "images": [{"url": "https://shirtonomy.se/media/store/img/fabrics/product-65-6vc0_L.jpg", "path": "full/0f/0fc6affb9d5ff408815b983468716aa83057ead7.jpg", "checksum": "5a8c2771f0d6ba892d8cbb99b21b3f15"}], "stock": "50", "in_stock": true, "name": "Sky Puppy Twill"}' )
        #json_scraped = simplejson.loads( """{"sku": "4324000", "category": "Womenswear / Dresses / Dresses - Evening", "vendor": "asos", "description": "John Zack Petite Embellished Bodice Maxi Dress With Tulle Skirt", "regular_price": "631.57", "url": "http://ad.zanox.com/ppc/?19595318C106179573&ULP=[[John-Zack-Petite/John-Zack-Petite-Embellished-Bodice-Maxi-Dress-With-Tulle-Skirt/Prod/pgeproduct.aspx?iid=6020396&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=qiipqlwrt&istBid=t&channelref=affiliate]]", "gender": "Womenswear / Dresses / Dresses - Evening", "brand": "John Zack Petite", "discount_price": "None", "image_urls": ["http://images.asos-media.com/inv/media/6/9/3/0/6020396/cream/image1xxl.jpg"], "name": "John Zack Petite Embellished Bodice Maxi Dress With Tulle Skirt - Cream", "currency": "SEK", "colors": "Cream", "affiliate": "zanox", "key": "http://www.asos.com/John-Zack-Petite/John-Zack-Petite-Embellished-Bodice-Maxi-Dress-With-Tulle-Skirt/Prod/pgeproduct.aspx?iid=6020396&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=qiipqlwrt&istBid=t&channelref=affiliate", "images": [{"url": "http://images.asos-media.com/inv/media/6/9/3/0/6020396/cream/image1xxl.jpg", "path": "full/58/587206339818aa3feae842d01f99678db24b70ec.jpg", "checksum": "a55b86a89170529a04c0b9b68bd5b5d5"}], "in_stock": true, "stock": ""}, "site_product": 2886305,}""")
