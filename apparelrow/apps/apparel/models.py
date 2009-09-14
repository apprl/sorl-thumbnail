from django.db import models
from django.contrib.auth.models import User

import mptt

class Manufacturer(models.Model):
    name = models.CharField(max_length=50)
    def __unicode__(self):
        return self.name

class ProductCategory(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')
    def __unicode__(self):
        return self.name

mptt.register(ProductCategory, order_insertion_by=['name'])

class Product(models.Model):
    GENDER_CHOICES = (
        ('F', 'Female'),
        ('M', 'Male'),
        ('U', 'Unisex'),
    )
    manufacturer = models.ForeignKey(Manufacturer)
    product_id = models.CharField(max_length=100)
    product_type = models.ForeignKey(ProductCategory)
    model_name = models.CharField(max_length=200)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    def __unicode__(self):
        return "%s %s %s" % (self.manufacturer, self.model_name, self.product_type)

class Look(models.Model):
    title = models.CharField(max_length=200)
    products = models.ManyToManyField(Product)
    user = models.ForeignKey(User)
    image = models.ImageField(upload_to='looks')
    def __unicode__(self):
        return "%s by %s" % (self.title, self.user)

# Create your models here.
