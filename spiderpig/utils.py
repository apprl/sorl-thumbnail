# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'

from cStringIO import StringIO
from zipfile import ZipFile


def unzip(data):
    """
    Unzip the given data and return as much data as possible.
    Expects a str.
    """
    f = ZipFile(StringIO(data))
    output = ''
    for tmpfile in f.infolist():
        output += f.open(tmpfile).read()
    return output


def is_zipped(response):
    """Return True if the response is zipped, or False otherwise"""
    ctype = response.headers.get('Content-Type', '')
    return ctype in ('application/zip',)
