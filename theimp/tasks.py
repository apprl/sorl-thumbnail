# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'

from theimp.models import Product
from celery.task import task
from theimp.parser import Parser

parser = Parser()
import logging

log = logging.getLogger("theimp")

@task(name='theimp.scrape_parse',max_retries=5, ignore_result=True)
def parse_theimp_product(product_id):
    log.info("Async parsing of product {}".format(product_id))
    product = Product.objects.get(pk=product_id)
    parser.parse(product)
    return True