# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding model 'VendorFeed'
        db.create_table('importer_vendorfeed', (
            ('username', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('comment', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('vendor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Vendor'])),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=15)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=2550)),
            ('decompress', self.gf('django.db.models.fields.CharField')(max_length=10, null=True, blank=True)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('provider_class', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('importer', ['VendorFeed'])

        # Adding model 'ImportLog'
        db.create_table('importer_importlog', (
            ('status', self.gf('django.db.models.fields.CharField')(default='running', max_length=10)),
            ('vendor_feed', self.gf('django.db.models.fields.related.ForeignKey')(related_name='import_log', to=orm['importer.VendorFeed'])),
            ('start_time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('imported_products', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('end_time', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('importer', ['ImportLog'])

        # Adding model 'ImportLogMessage'
        db.create_table('importer_importlogmessage', (
            ('status', self.gf('django.db.models.fields.CharField')(default='info', max_length=10)),
            ('message', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('import_log', self.gf('django.db.models.fields.related.ForeignKey')(related_name='messages', to=orm['importer.ImportLog'])),
            ('datetime', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('importer', ['ImportLogMessage'])

        # Adding model 'FXRate'
        db.create_table('importer_fxrate', (
            ('currency', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('base_currency', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('rate', self.gf('django.db.models.fields.DecimalField')(max_digits=10, decimal_places=6)),
        ))
        db.send_create_signal('importer', ['FXRate'])

        # Adding unique constraint on 'FXRate', fields ['base_currency', 'currency']
        db.create_unique('importer_fxrate', ['base_currency', 'currency'])

        # Adding model 'ColorMapping'
        db.create_table('importer_colormapping', (
            ('color', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('aliases', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('importer', ['ColorMapping'])
    
    
    def backwards(self, orm):
        
        # Deleting model 'VendorFeed'
        db.delete_table('importer_vendorfeed')

        # Deleting model 'ImportLog'
        db.delete_table('importer_importlog')

        # Deleting model 'ImportLogMessage'
        db.delete_table('importer_importlogmessage')

        # Deleting model 'FXRate'
        db.delete_table('importer_fxrate')

        # Removing unique constraint on 'FXRate', fields ['base_currency', 'currency']
        db.delete_unique('importer_fxrate', ['base_currency', 'currency'])

        # Deleting model 'ColorMapping'
        db.delete_table('importer_colormapping')
    
    
    models = {
        'apparel.vendor': {
            'Meta': {'object_name': 'Vendor'},
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logotype': ('django.db.models.fields.files.ImageField', [], {'max_length': '127', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'})
        },
        'importer.colormapping': {
            'Meta': {'object_name': 'ColorMapping'},
            'aliases': ('django.db.models.fields.TextField', [], {}),
            'color': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'importer.fxrate': {
            'Meta': {'unique_together': "(('base_currency', 'currency'),)", 'object_name': 'FXRate'},
            'base_currency': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rate': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '6'})
        },
        'importer.importlog': {
            'Meta': {'object_name': 'ImportLog'},
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imported_products': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'running'", 'max_length': '10'}),
            'vendor_feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'import_log'", 'to': "orm['importer.VendorFeed']"})
        },
        'importer.importlogmessage': {
            'Meta': {'object_name': 'ImportLogMessage'},
            'datetime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_log': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': "orm['importer.ImportLog']"}),
            'message': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'info'", 'max_length': '10'})
        },
        'importer.vendorfeed': {
            'Meta': {'object_name': 'VendorFeed'},
            'comment': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'decompress': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '15'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'provider_class': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '2550'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['apparel.Vendor']"})
        }
    }
    
    complete_apps = ['importer']
