import os, datetime
#from datetime import datetime
from django.db.models import Model
from django.db.models.query import QuerySet
from django.db.models.fields.files import FieldFile
from django.db.models.fields.related import ForeignKey, ManyToManyField
from django.utils.functional import Promise

from django.utils.simplejson import encoder


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
    
    # FIXME: Add options for how relationships should be followed
    # FIXME: Add class to encapsulate encoded JSON 
    # FIXME: Special case JSON objects so they do not get processed again 
    #        (just concatinate them to base string). This would allow caching
    #        on object level
    
        
    def default(self, o):
        """
        Returns iterable for non-native objects
        """
        
        if isinstance(o, FieldFile):
            if str(o):
                return o.url
            else:
                return u''
            
        elif isinstance(data, Decimal):
           # FIXME: Can you turn this into a primitive, like a float or something
           # instead and let the core module handle the conversion to string? 
            return str(data)
        
        elif isinstance(o, QuerySet):
            return list(o)
        
        elif isinstance(o, Model):
            return self.encode_model(o)   # Should return a dictionary
        
        # FIXME: Does these objects have a common superclass?
        elif (isinstance(o, datetime.datetime) or 
              isinstance(o, datetime.time)  or 
              isinstance(o, datetime.date)):
            
            return o.isoformat()
        
        else:
            return encoder.JSONEncoder.default(self, o)
    
    
    
    def encode_model(self, model):
        """
        Iterates over a model, follows relationships and properly handles field
        data.
        """
        ret     = {}
        builtin = dir(model.__class__)
        
        # Get database fields and any many_to_many relationships
        for f in model._meta.fields + model._meta.many_to_many:
            field, value = self.model_field(model, f)
            ret[field]   = value
            
            # Save the custom field, plus the new field
            builtin.extend([field, f.attname])
        
        # Add runtime properties
        for f in [k for k in dir(model) if k not in builtin]:
            # FIXME: Note sure to call encode() from here...
            ret[f] = getattr(model, f)
        
        return ret
    
    def model_field(self, model ,field):
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




def encode(o):
    """
    Creates a basic encoder with no options and encodes the given object.
    """
    return ExtendedJSONEncoder().encode(o)
