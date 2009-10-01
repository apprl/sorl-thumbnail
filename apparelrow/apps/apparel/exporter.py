from django.db.models.fields import FieldDoesNotExist
from django.db.models.fields.related import ForeignKey, ManyToManyField, RelatedObject, OneToOneField

from pprint import pprint
    

def export_model(instance):
    """
    This routine determines what fields should be exported from the model, and
    what relationships should be followed.
    
    Returns a dictionary with exported data. Values are not manipulated, 
    relationships are represented as model instances.
    
    See the Exporter class for details.
    """

    ret  = {}
    seen = dir(instance.__class__)
    meta = instance._meta
    
    # Try to add value from each field by looking at the class' metadata
    for name in meta.get_all_field_names():
        try:
            field     = meta.get_field_by_name(name)[0]
            ret[name] = field_value(instance, field)
        
        except (FieldDoesNotExist, ExcludeField), e:
            continue
        
        finally:
            if hasattr(field, 'attname'):
                seen.append(field.attname)
    
    # If there are explicit fields, or if export_transient_fields is true,
    # add runtime fields/values that is not already seen, or is a built-in
    exp = ModelExporter.get_instance(instance)
    
    # FIXME: Move logic to Exporter object'
    # FIXME: Remove this altogether?
    if exp.export_fields is not None or exp.export_transient_fields:
        possible = exp.export_fields if exp.export_fields else dir(instance)

        for attr in [f for f in possible if f not in seen and not f[0] == '_' ]:
            # This will ignore fields already treated and those deemed private (prefixed with _)
            try:
                ret[attr] = getattr(instance, attr)
            except AttributeError:
                pass
    
    return ret

    
def field_value(instance, field):
    """
    Returns a value for the given field. Throws an ExcludeField exception if this
    field should be excluded from the export dictionary.
    """
    
    # FIXME: Move all of this logic to the exporter instance
    
    exp = ModelExporter.get_instance(instance)
    
    if not exp.include_field(field):
        raise ExcludeField(field.name)
    
    if isinstance(field, RelatedObject):
        # Special case related object as it has no attribute value
        
        value = field.model.objects.filter(**{field.field.name: instance})
        
        # Because we're following a relationship backward, add a note on the
        # targets Exporter instance that it shouldn't follow the relationship back here
        for model in value:
            ModelExporter.get_instance(model)._circular.append(field.field.name)
        
    else:
        value = getattr(instance, field.attname)  # Get raw object value
    
    if value is None:
        pass
    
    elif isinstance(field, ForeignKey):
        value = field.related.parent_model.objects.get(id=value)
    
    elif isinstance(field, ManyToManyField):
        value = value.all()
    
    return value
    

class ExcludeField(Exception):
    """
    When raised, indicates that the current field should not be included in the
    exporter.
    """
    pass

class ExporterCache():
    """
    Wraps cached output so that encoders can recogise cached data.
    """
    
    def __init__(self, data, type):
        self.data = data
        self.type = type
    
    def __unicode__(self):
        return self.data


class ModelExporter():
    """
    This class allows the exporter module to let Django objects to control how 
    they should be exported.
    
    Synopsis
    
        class Book(models.Model):
            author     = models.ForeignKey(Author)
            categories = models.ManyToManyField(Category)
            title      = models.CharField(...)
            not_pub    = models.CharField(...)
            
            ...
            
            class Exporter():
                export_fields       = ['author', 'title']
                follow_indirect_rel = False
        
        book = Book()
        exporter = Exporter.get_instance(book)
        
        if 'field' in exporter.export_fields:
            print "Should be exported"
    
    Note that the exporter will work on any Django model instance without having
    to declare the inline Exporter class. In that case, a default ModelExporter
    is used. 
    
    These properties of the inline module controls the exporters behaviour
    
     - export_fields
       List, None
       A list of fields to export. If defined, these fields will be exported
       regardless of other settings. If omitted or None, all fields will
       be exported.
       Special values:
        * __all__   Synonym for all declared fields
     
     - follow_direct_rel
       Boolean, True
       If True, explicitly defined relationships, (ForeignKey, ManyToMany and 
       OneToOne) relationships will be followed. If export_fields is set, 
       this setting has no effect.
       
     - follow_indirect_rel
       Boolean, False
       If True, indirect relationships (or "reverse" relationships) will be 
       followed. If export_fields is set, this setting has no effect.
     
     - export_transient_fields
       Boolean, True
       If True, non-persistant attributes that has been added in runtime will
       be added to the exported data.  If export_fields is set, this setting 
       has no effect.
    """
    
    # FIXME:
    #   - Add "+" prefix to export_fields that will override other setting
    
    
    def __init__(self, model):
        # Initialise exporter attributes with data from exp
        self.model                   = model
        self.export_fields           = None
        self.follow_direct_rel       = True
        self.follow_indirect_rel     = False
        self.export_transient_fields = True
        self._circular               = []
        self._cache                  = {}
        
        if hasattr(model, 'Exporter'):
            for attr in self.__dict__:
                if attr == 'model':
                    continue
                
                if hasattr(model.Exporter, attr):
                    setattr(self, attr, getattr(model.Exporter, attr))
        
        if self.export_fields:
            try:
                self.export_fields.remove('__all__')
            except ValueError:
                pass
            else:
                # Add all physical fields, and all declared relationships
                all_fields = self.model._meta.fields + self.model._meta.many_to_many
                
                self.export_fields.extend(map(lambda x: x.name, all_fields))
            
            for field in filter(lambda x: x.find('-') == 0, self.export_fields):
                try:
                    self.export_fields.remove(field)            # Remove the -field
                    self.export_fields.remove(field[1:])        # Remove the field it indicates
                except ValueError:
                    pass
    
    def cache_output(self, data, type):
        self._cache[type] = ExporterCache(data, type)
    
    def include_field(self, field):
        """
        Given a django.db.models.fields.Field object, returns True or False 
        whether it should be included in export or not.
        """
        
        field_name = ModelExporter.get_field_name(field)
        
        if field_name in self._circular:
            # If this field is marked as circular, pop it from the list
            # and return
            self._circular.remove(field_name)
            return False
        
        if self.export_fields is not None:
            # export_fields list is explicit and no other rules apply
            return True if field_name in self.export_fields else False
        
        if (isinstance(field, ForeignKey) or 
            isinstance(field, ManyToManyField) or
            isinstance(field, OneToOneField)):
            return True if self.follow_direct_rel else False
        
        if isinstance(field, RelatedObject):
            return True if self.follow_indirect_rel else False
          
        return True
    
    
    @staticmethod
    def get_field_name(field):
        try:
            return field.var_name
        except AttributeError:
            return field.name
    
    @staticmethod
    def get_instance(model_instance):
        """
        Static method. Returns the ModelExporter instance for the given model 
        instance.
        
        This will assign a new ModelExporter instance to the model if not already
        present.
        """
        
        try:
            return model_instance._exporter
        
        except AttributeError:
            model_instance._exporter = ModelExporter(model_instance)
            return model_instance._exporter
