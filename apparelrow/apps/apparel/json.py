import os
import datetime
from decimal import Decimal

from django.core.serializers.json import DateTimeAwareJSONEncoder
from django.db.models import Model
from django.db.models.query import QuerySet
from django.db.models.fields.related import ForeignKey, ManyToManyField
from django.db.models.fields.files import FieldFile
from django.template.loader import render_to_string
from django.utils import simplejson
from django.utils.functional import Promise
from django.utils.encoding import force_unicode
from pprint import pprint

def encode(data):
    """
    Returns a JSON string with the data in data.
    """

    def _any(data):
        """
        Encodes a piece of data. This will deligate to encoders for specific
        fields and hence it is recursive.
        
        """
        ret = None
        
        if isinstance(data, FieldFile):
            if str(data):
                ret = data.url
            else:
                ret = u''
            
        elif isinstance(data, Decimal):
            ret = str(data)
        
        elif isinstance(data, QuerySet):
            ret = _list(data)
        
        elif isinstance(data, Model):
            ret = _model(data)

        # see http://code.djangoproject.com/ticket/5868
        elif isinstance(data, Promise):
            ret = force_unicode(data)
                
        elif isinstance(data, datetime.datetime):
            # FIXME: Explicitly export as ISO string
            ret = str(data).replace(' ', 'T')

        elif isinstance(data, datetime.date):
            # FIXME: Excplictly export as ISO string
            ret = str(data)

        elif isinstance(data, datetime.time):
            # FIXME: Excplictly export as ISO string
            ret = "T" + str(data)

        elif isinstance(data, basestring):
            ret = unicode(data)
        
        elif isinstance(data, dict):
            ret = _dict(data)
        
        elif isinstance(data, list):
            # FIXME: Treat anything that is iterable as list?
            ret = _list(data)
        else:
            ret = data

        return ret
    
    def _field(model, field):
        """
        Preprocess data in a model field. This is primary used to follow 
        relationships.
        
        Returns two values, field and value
        """
        
        name  = field.attname
        value = getattr(model, name)
        
        if value is None:
            pass
        
        elif isinstance(field, ForeignKey):
            name  = field.name
            value = field.related.parent_model.objects.get(id=value)
        
        elif isinstance(field, ManyToManyField):
            name  = field.name
            value = getattr(model, name).all()
        
        return name, value
        
    
    def _model(data):
        ret     = {}
        builtin = dir(data.__class__)
        
        # Get database fields and any many_to_many relationships
        for f in data._meta.fields + data._meta.many_to_many:
            field, value = _field(data, f)
            ret[field]   = _any(value)
            
            # Save the custom field, plus the new field
            builtin.extend([field, f.attname])
        
        # Add runtime properties
        for f in [k for k in dir(data) if k not in builtin]:
           ret[f] = _any(getattr(data, f))

        return ret


    def _list(data):       
        return [_any(v) for v in data]
    
    def _dict(data):
        return dict([(k, _any(v)) for k, v in data.items()])
    
    
    
    ret = _any(data)
    
    return simplejson.dumps(ret, cls=DateTimeAwareJSONEncoder)



