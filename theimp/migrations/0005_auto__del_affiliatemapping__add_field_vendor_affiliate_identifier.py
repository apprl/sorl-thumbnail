# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'AffiliateMapping'
        db.delete_table(u'theimp_affiliatemapping')

        # Adding field 'Vendor.affiliate_identifier'
        db.add_column(u'theimp_vendor', 'affiliate_identifier',
                      self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Adding model 'AffiliateMapping'
        db.create_table(u'theimp_affiliatemapping', (
            ('vendor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['theimp.Vendor'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('identifier', self.gf('django.db.models.fields.CharField')(max_length=128)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'theimp', ['AffiliateMapping'])

        # Deleting field 'Vendor.affiliate_identifier'
        db.delete_column(u'theimp_vendor', 'affiliate_identifier')


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
        u'theimp.mapping': {
            'Meta': {'object_name': 'Mapping'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mapping_aliases': ('django.db.models.fields.TextField', [], {}),
            'mapping_key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'mapping_type': ('django.db.models.fields.CharField', [], {'max_length': '24'})
        },
        u'theimp.product': {
            'Meta': {'object_name': 'Product'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dropped': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
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
            'affiliate_identifier': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        }
    }

    complete_apps = ['theimp']