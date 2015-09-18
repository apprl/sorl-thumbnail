# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'

import zipfile
from scrapy.http import Response
import os
from django.test import TestCase

class TestScrapyMiddleWare(TestCase):
    testzipfile = None
    encrypted_data = None
    decrypted_data = None
    encrypted_file = None

    def setUp(self):
        from django.conf import settings
        self.testzipfile = os.path.join(settings.PROJECT_ROOT,'../misc/test.csv.zip')
        self.encrypted_file = open(self.testzipfile, 'r')

        en_output = ''
        for line in self.encrypted_file.readlines():
            en_output += line
        self.encrypted_data = en_output

        zf = zipfile.ZipFile(self.testzipfile)
        data_read = None
        for tmpfile in zf.infolist():
            data_read = zf.open(tmpfile).read()
        zf.close()
        self.decrypted_data = data_read

    def tearDown(self):
        self.encrypted_file.close()

    def test_middleware(self):
        """
        Test for middleware detection of incoming zipfiles both by reading the filename and the
        characteristics signature of the file.
        """
        from .spidercrawl.middlewares import DownloadZipMiddleware
        response = Response(url="http://someurl.com/bjornborg.csv.zip")
        response = response.replace(body=self.encrypted_data)
        middleware = DownloadZipMiddleware()
        assert middleware.custom_is_zipped(response) == True
        response_decrypted = middleware.process_response(request=None,response=response,spider=None)
        assert response_decrypted.body[:100] == self.decrypted_data[:100]

    def test_unzip(self):
        """
        Test for unpacking zipfile
        """
        from .utils import unzip
        data_test = self.encrypted_data
        print unzip(data_test)[:100]
        print self.decrypted_data[:100]
        assert unzip(data_test)[:100] == self.decrypted_data[:100]
