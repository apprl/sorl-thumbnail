# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'VendorFeed'
        db.create_table(u'importer_vendorfeed', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('vendor', self.gf('django.db.models.fields.related.OneToOneField')(related_name='vendor_feed', unique=True, to=orm['apparel.Vendor'])),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=15)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=2550)),
            ('username', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('decompress', self.gf('django.db.models.fields.CharField')(max_length=10, null=True, blank=True)),
            ('provider_class', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('comment', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
        ))
        db.send_create_signal(u'importer', ['VendorFeed'])

        # Adding model 'ImportLog'
        db.create_table(u'importer_importlog', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('start_time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('end_time', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('status', self.gf('django.db.models.fields.CharField')(default='running', max_length=10)),
            ('vendor_feed', self.gf('django.db.models.fields.related.ForeignKey')(related_name='import_log', to=orm['importer.VendorFeed'])),
            ('imported_products', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal(u'importer', ['ImportLog'])

        # Adding model 'ImportLogMessage'
        db.create_table(u'importer_importlogmessage', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('import_log', self.gf('django.db.models.fields.related.ForeignKey')(related_name='messages', to=orm['importer.ImportLog'])),
            ('status', self.gf('django.db.models.fields.CharField')(default='info', max_length=10)),
            ('message', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('datetime', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'importer', ['ImportLogMessage'])

        # Adding model 'FXRate'
        db.create_table(u'importer_fxrate', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('base_currency', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('currency', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('rate', self.gf('django.db.models.fields.DecimalField')(max_digits=10, decimal_places=6)),
        ))
        db.send_create_signal(u'importer', ['FXRate'])

        # Adding unique constraint on 'FXRate', fields ['base_currency', 'currency']
        db.create_unique(u'importer_fxrate', ['base_currency', 'currency'])

        # Adding model 'Mapping'
        db.create_table(u'importer_mapping', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('mapping_type', self.gf('django.db.models.fields.CharField')(max_length=24)),
            ('mapping_key', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('mapping_aliases', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'importer', ['Mapping'])


    def backwards(self, orm):
        # Removing unique constraint on 'FXRate', fields ['base_currency', 'currency']
        db.delete_unique(u'importer_fxrate', ['base_currency', 'currency'])

        # Deleting model 'VendorFeed'
        db.delete_table(u'importer_vendorfeed')

        # Deleting model 'ImportLog'
        db.delete_table(u'importer_importlog')

        # Deleting model 'ImportLogMessage'
        db.delete_table(u'importer_importlogmessage')

        # Deleting model 'FXRate'
        db.delete_table(u'importer_fxrate')

        # Deleting model 'Mapping'
        db.delete_table(u'importer_mapping')


    models = {
        u'apparel.vendor': {
            'Meta': {'ordering': "['name']", 'object_name': 'Vendor'},
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logotype': ('django.db.models.fields.files.ImageField', [], {'max_length': '127', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'})
        },
        u'importer.fxrate': {
            'Meta': {'unique_together': "(('base_currency', 'currency'),)", 'object_name': 'FXRate'},
            'base_currency': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rate': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '6'})
        },
        u'importer.importlog': {
            'Meta': {'ordering': "['-start_time']", 'object_name': 'ImportLog'},
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imported_products': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'running'", 'max_length': '10'}),
            'vendor_feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'import_log'", 'to': u"orm['importer.VendorFeed']"})
        },
        u'importer.importlogmessage': {
            'Meta': {'object_name': 'ImportLogMessage'},
            'datetime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_log': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': u"orm['importer.ImportLog']"}),
            'message': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'info'", 'max_length': '10'})
        },
        u'importer.mapping': {
            'Meta': {'object_name': 'Mapping'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mapping_aliases': ('django.db.models.fields.TextField', [], {}),
            'mapping_key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'mapping_type': ('django.db.models.fields.CharField', [], {'max_length': '24'})
        },
        u'importer.vendorfeed': {
            'Meta': {'object_name': 'VendorFeed'},
            'comment': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'decompress': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '15'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'provider_class': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '2550'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'vendor': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'vendor_feed'", 'unique': 'True', 'to': u"orm['apparel.Vendor']"})
        }
    }

    complete_apps = ['importer']