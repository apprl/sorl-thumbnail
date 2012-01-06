# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Deleting model 'ColorMapping'
        db.delete_table('importer_colormapping')

        # Adding model 'Mapping'
        db.create_table('importer_mapping', (
            ('mapping_aliases', self.gf('django.db.models.fields.TextField')()),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('mapping_key', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('mapping_type', self.gf('django.db.models.fields.CharField')(max_length=24)),
        ))
        db.send_create_signal('importer', ['Mapping'])
    
    
    def backwards(self, orm):
        
        # Adding model 'ColorMapping'
        db.create_table('importer_colormapping', (
            ('color', self.gf('django.db.models.fields.CharField')(max_length=100, unique=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('aliases', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('importer', ['ColorMapping'])

        # Deleting model 'Mapping'
        db.delete_table('importer_mapping')
    
    
    models = {
        'apparel.vendor': {
            'Meta': {'object_name': 'Vendor'},
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logotype': ('django.db.models.fields.files.ImageField', [], {'max_length': '127', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'})
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
        'importer.mapping': {
            'Meta': {'object_name': 'Mapping'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mapping_aliases': ('django.db.models.fields.TextField', [], {}),
            'mapping_key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'mapping_type': ('django.db.models.fields.CharField', [], {'max_length': '24'})
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
