from django.db.models.fields import FieldDoesNotExist
from django.db.models.fields.related import ForeignKey, ManyToManyField, RelatedObject


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
            print 'Skipping field: %s' % e            # FIXME: Only print on debug
            continue
            
        finally:
            if hasattr(field, 'attname'):
                seen.append(field.attname)
    
    
    # If there are explicit fields, or if export_transient_fields is true,
    # add runtime fields/values that is not already seen, or is a built-in
    exp = Exporter.get_instance(instance)
    
    # FIXME: Move logic to Exporter object
    if exp.export_fields is not None or exp.export_transient_fields:
        possible = exp.export_fields if exp.export_fields else dir(instance)

        for attr in [f for f in possible if f not in seen ]:
            ret[attr] = getattr(instance, attr)
    
    return ret
        
    
def field_value(instance, field):
    """
    Returns a value for the given field. Throws an ExcludeField exception if this
    field should be excluded from the export dictionary.
    """
    exp = Exporter.get_instance(instance)
    
    if not exp.include_field(field):
        raise ExcludeField(field.name)
    
    
    if isinstance(field, RelatedObject):
        # Special case related object as it has no attribute value
        # EXPORT RELATED OBJECT
        print "EXPORt RELATED OBJECT"
        return None
    
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
                export_fields   = ['author', 'title']
                follow_indirect = False
        
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
    #   - Add "-" prefix to export_fields which will remove them from list, so
    #     you can do ['__all__', '-id', ...]
    #
    #   - Add "+" prefix to export_fields that will override other setting
    
    
    __init__(self, model):
        # Initialise exporter attributes with data from exp
        self.model                   = model
        self.export_fields           = None
        self.follow_direct_rel       = True
        self.follow_indirect_rel     = False
        self.export_transient_fields = True
        
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
                self.export_fields.extend(self.model._meta.fields)
        
    
    def include_field(field):
        """
        Given a django.db.models.fields.Field object, returns True or False 
        whether it should be included in export or not.
        """
        if self.export_fields is not None and field.name in self.export_fields:
            return True
        
        if follow_direct_rel and (isinstance(field, ForeignKey) or 
                                  isinstance(field, ManyToManyField) or
                                  isinstance(field, OneToOneField)):
            return True
        
        if follow_indirect_rel and isinstance(field, RelatedObject):
            return True
             
        return False
    
    
    @staticmethod
    def get_instance(model_instance):
        """
        Static method. Returns the ModelExporter instance for the given model 
        instance.
        
        This will assign a new ModelExporter instance to the model if not already
        present.
        """
        
        try:
            return instance._exporter
        
        except AttributeError:
            instance._exporter = ModelExporter(instance)
            return instance._exporter
