import os, datetime
from django.db.models import Model
from django.db.models.query import QuerySet
from django.db.models.fields.files import FieldFile
from django.utils.functional import Promise
from django.utils.simplejson import encoder

from decimal import Decimal

from apps.apparel import exporter


class ExtendedJSONEncoder(encoder.JSONEncoder):
    """
    Extends the Django encoder to deal with Django models, relationships and
    other non-primitive objects.
    
    Usage
    
        from ...json import encode
        
        json = encode(thing)
    
    or
    
        from ...json import ExtendedJSONEncoder
        
        encoder = ExtendedJSONEncoder(**opts)
        json = encoder.encode(thing)
    
    See documentation for django.utils.simplejson.encoder.JSONEncoder for list
    of available options.
    """
            
    def default(self, o):
        """
        Returns iterable for non-native objects
        """
        
        if isinstance(o, FieldFile):
            if str(o):
                return o.url
            else:
                return u''

        elif isinstance(o, QuerySet):
            return list(o)
        
        elif isinstance(o, Model):
            return exporter.export_model(o)
        
        elif isinstance(o, Decimal):
            return str(o)
        
        # FIXME: Does these objects have a common superclass?
        elif (isinstance(o, datetime.datetime) or 
              isinstance(o, datetime.time)  or 
              isinstance(o, datetime.date)):
            
            return o.isoformat()
        
        else:
            return encoder.JSONEncoder.default(self, o)


def encode(o):
    """
    Creates a basic encoder with no options and encodes the given object.
    """
    return ExtendedJSONEncoder().encode(o)
