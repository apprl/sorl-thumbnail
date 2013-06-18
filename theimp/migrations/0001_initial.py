# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Product'
        db.create_table(u'theimp_product', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('json', self.gf('django.db.models.fields.TextField')()),
            ('is_auto_validated', self.gf('django.db.models.fields.NullBooleanField')(default=None, null=True, blank=True)),
            ('is_manual_validated', self.gf('django.db.models.fields.NullBooleanField')(default=None, null=True, blank=True)),
            ('merged', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['theimp.Product'], null=True, blank=True)),
            ('vendor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['theimp.Vendor'])),
        ))
        db.send_create_signal(u'theimp', ['Product'])

        # Adding model 'Vendor'
        db.create_table(u'theimp_vendor', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal(u'theimp', ['Vendor'])

        # Adding model 'BrandMapping'
        db.create_table(u'theimp_brandmapping', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('vendor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['theimp.Vendor'])),
            ('brand', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('mapped_brand', self.gf('django.db.models.fields.CharField')(max_length=512)),
        ))
        db.send_create_signal(u'theimp', ['BrandMapping'])

        # Adding model 'CategoryMapping'
        db.create_table(u'theimp_categorymapping', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('vendor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['theimp.Vendor'])),
            ('category', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('mapped_category', self.gf('django.db.models.fields.CharField')(max_length=512)),
        ))
        db.send_create_signal(u'theimp', ['CategoryMapping'])


    def backwards(self, orm):
        # Deleting model 'Product'
        db.delete_table(u'theimp_product')

        # Deleting model 'Vendor'
        db.delete_table(u'theimp_vendor')

        # Deleting model 'BrandMapping'
        db.delete_table(u'theimp_brandmapping')

        # Deleting model 'CategoryMapping'
        db.delete_table(u'theimp_categorymapping')


    models = {
        u'theimp.brandmapping': {
            'Meta': {'object_name': 'BrandMapping'},
            'brand': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mapped_brand': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['theimp.Vendor']"})
        },
        u'theimp.categorymapping': {
            'Meta': {'object_name': 'CategoryMapping'},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mapped_category': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['theimp.Vendor']"})
        },
        u'theimp.product': {
            'Meta': {'object_name': 'Product'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_auto_validated': ('django.db.models.fields.NullBooleanField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'is_manual_validated': ('django.db.models.fields.NullBooleanField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'json': ('django.db.models.fields.TextField', [], {}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'merged': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['theimp.Product']", 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['theimp.Vendor']"})
        },
        u'theimp.vendor': {
            'Meta': {'object_name': 'Vendor'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        }
    }

    complete_apps = ['theimp']