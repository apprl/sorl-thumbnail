from django.db import models

class LookManager(models.Manager):
    """
    Adds a shortcut to get published looks only.
    """
    def get_query_set(self):
        queryset = super(LookManager, self).get_query_set() \
                                           .filter(published=True)

        return queryset

class ProductManager(models.Manager):
    """
    Adds a shortcut to get valid products only.
    """
    def __init__(self, *args, **kwargs):
        if 'availability' in kwargs:
            self.availability = kwargs['availability']
            del kwargs['availability']

        super(ProductManager, self).__init__(*args, **kwargs)

    def get_query_set(self):
        queryset = super(ProductManager, self).get_query_set() \
                                              .filter(published=True)
        if self.availability:
            queryset = queryset.filter(vendorproduct__isnull=False, availability=True)

        return queryset
