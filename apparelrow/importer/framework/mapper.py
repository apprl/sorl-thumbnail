# -*- coding: utf-8 -*-
import re
import logging
import datetime
import htmlentitydefs
import itertools
import decimal

from django.conf import settings
from django.utils.encoding import smart_unicode

from apparelrow.importer.api import API, SkipProduct
from apparelrow.importer.models import Mapping

logger = logging.getLogger('apparel.importer.mapper')

# Compile regular expression matching all aliases to a color, should only be
# compiled once on import.
COLOR_REGEXES = dict(
    (m.mapping_key, re.compile(ur'\b(?:%s)\b' % (ur'|'.join(m.get_list()),), re.I | re.UNICODE))
    for m in Mapping.objects.filter(mapping_type='color')
)

PATTERN_REGEXES = dict(
    (m.mapping_key, re.compile(ur'\b(?:%s)\b' % (ur'|'.join(m.get_list()),), re.I | re.UNICODE))
    for m in Mapping.objects.filter(mapping_type='pattern')
)

GENDER_REGEXES = dict(
    (m.mapping_key, re.compile(ur'\b(?:%s)\b' % (ur'|'.join(m.get_list()),), re.I | re.UNICODE))
    for m in Mapping.objects.filter(mapping_type='gender')
)


class DataMapper(object):
    color_regexes = None
    re_html     = re.compile(r'<.+?>', re.S)
    re_trunc_ws = re.compile(r'[ \t\r]{2,}')
    re_trim     = re.compile(r'^\s*|\s*$')

    IMAGE_LARGE = 20000
    IMAGE_MEDIUM = 5000
    IMAGE_SMALL = 1000
    
    def __init__(self, provider, record={}):
        self.provider      = provider    # Reference to the provider instance
        self.record        = record      # Raw data record source file
        self.mapped_record = {}
    
    def preprocess(self):
        """
        This method is called immidiately before field mapping begins. The 
        current record can be found in self.record.
        Does not expect any return value.
        """
        pass
    
    def postprocess(self):
        """
        This method is called immidiately after field mappings are complete. The
        mapped data can be found in self.mapped_record, and the raw data in 
        self.record
        
        By default, postprocess performs following actions
        
         * Leading and trailing whitespaces are trimmed
         * HTML is stripped from the description, product-name, category and manufacturer field
         * HTML entities are expanded to unicode characters in the description, product-name, category and manufacturer field
         * Add a special field to the product, called patterns
        
        """
        
        for field, value in self.mapped_record['product'].items():
            self.mapped_record['product'][field] = self.trim(value)

        for field in ['product-name', 'description', 'category', 'manufacturer']:
            self.mapped_record['product'][field] = self.strip_html(self.mapped_record['product'][field])

        self.mapped_record['product']['patterns'] = self.map_patterns(self.mapped_record['product'].get('product-name', '') + self.mapped_record['product'].get('description'))

        # Remove manufacturer from product name
        product_name = re.sub(r'(?iu)^%s' % (re.escape(self.mapped_record['product']['manufacturer']),), '', self.mapped_record['product']['product-name'], count=1)
        product_name = product_name.lstrip(' -_')
        if product_name:
            product_name = product_name[0].upper() + product_name[1:]
            self.mapped_record['product']['product-name'] = product_name

        price = self.mapped_record['product']['price']
        discount_price = self.mapped_record['product']['discount-price']

        # Skip product if price is not set
        if not price:
            raise SkipProduct('No price field set')

        # Skip product if price is invalid
        try:
            price = decimal.Decimal(price)
        except (decimal.InvalidOperation, ValueError, AttributeError, TypeError):
            raise SkipProduct('Not a valid price')

        # Skip product if price is less than or equal to zero
        if price <= decimal.Decimal('0.00'):
            raise SkipProduct('Price is less than or equal to zero')

        if discount_price:
            # Skip product if discount price is invalid
            try:
                discount_price = decimal.Decimal(discount_price)
            except (decimal.InvalidOperation, ValueError, AttributeError, TypeError):
                raise SkipProduct('Not a valid discount price')

            # Skip product if discount product is less than or equal to zero
            if discount_price <= decimal.Decimal('0.00'):
                raise SkipProduct('Discount price is less than or equal to zero')

            # If price and discount price is equal or discount price is larger,
            # there is no discount
            # TODO: is this ok?
            if price <= discount_price:
                self.mapped_record['product']['discount-price'] = None

    def translate(self):
        """
        Returns a hash of correctly formatted fields
        """
        self.preprocess()

        self.mapped_record.update({
            'version': '0.1',
            'date':    self.map_field('date') or datetime.datetime.now().strftime('%Y-%m-%dT%H:%m:%SZ%z'),
            'vendor':  self.provider.feed.vendor.name,
            'product': {}
        })
        
        for field in ('product-id', 
                      'product-name', 
                      'category',
                      'manufacturer', 
                      'price',
                      'discount-price',
                      'gender',
                      'currency', 
                      'delivery-cost', 
                      'delivery-time', 
                      'product-url', 
                      'description', 
                      'availability',):
            try:
                self.mapped_record['product'][field] = self.map_field(field)
            except SkipField:
                logger.debug(u'Skipping field %s' % field)
                continue

        self.mapped_record['product']['image-url'] = self.map_field('image_url') or []
        self.mapped_record['product']['variations'] = self.map_field('variations') or []
        
        self.postprocess()

        return self.mapped_record
    
    def map_field(self, field_name):
        """
        Returns a value for the given field. This method will first try to call
        a method called
        
            self.get_[field_name]
        
        (Note: Any occurence of - in the field name is represented by _ in the
        method name. So for field 'product-name', this method will attempt to
        call 'get_product_name')
        
        and if that does not exist it will try use a value stored in:
        
            self.record[field_name]
        
        else return None
        
        This method may throw a SkipField exception causing the field to be 
        skipped, but the process to continue.
        """
        
        method_name = 'get_%s' % field_name.replace('-', '_')
        
        if hasattr(self, method_name):
            return getattr(self, method_name)()
       
        return self.record.get(field_name)
    
    #
    # - Helper methods -
    #

    def map_colors(self, value=''):
        """
        Helper method that appempts to extract colour names from the given string
        and returns a list of names known by apparelrow.

        Example

        >>> mapper = DataMapper()
        >>> list = mapper.map_colors(u'Here is a string with Black, navy and red')
        ['black', 'blue', 'red']
        """
        return [c for c, r in COLOR_REGEXES.items() if r.search(smart_unicode(value))]

    def map_patterns(self, value=''):
        """
        Helper method that appempts to extract pattern names from the given string
        and returns a list of names known by apparelrow.

        Example

        >>> mapper = DataMapper()
        >>> list = mapper.map_patterns(u'Here is a string with striped clothes')
        ['striped']
        """
        return [c for c, r in PATTERN_REGEXES.items() if r.search(smart_unicode(value))]

    def map_gender(self, value=''):
        """
        Helper method that attempts to extract gender from the given string and
        returns the proper gender enum value.

        Example

        >>> mapper = DataMapper()
        >>> mapper.map_gender(u"Women's Accessories")
        W
        """
        for c, r in GENDER_REGEXES.items():
            if r.search(smart_unicode(value)):
                return c

        return None

    def strip_html(self, text):
        """
        Strings argument from all HTML-tags and expands HTML entities.
        """
        if text is None:
            return None

        return self.trim(
                    expand_entities(
                        self.re_html.sub(
                            ' ',
                            text
                        )
                    )
                )

    def trim(self, text):
        """
        Trims whitespaces to the left and right of text. Argument may be a list
        of strings which will be trimmed.
        """
        repl = lambda x: self.re_trunc_ws.sub(' ', self.re_trim.sub('', x))

        try:
            if isinstance(text, list):
                text = map(repl, text)
            else:
                text = repl(text)
        except TypeError:
            pass

        return text

def expand_entities(text):
    """
    Expands HTML entities from the given text.
    Written by Fredrik Lundh, http://effbot.org/zone/re-sub.htm#unescape-html
    """
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        
        return text # leave as is
    
    return re.sub("&#?\w+;", fixup, text)


class SkipField(Exception):
    """
    This is raised by a field mapper causing the field not to be mapped.
    """
    pass
