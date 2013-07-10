# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):
    depends_on = (
        ('apparel', '0001_initial'),
    )

    def forwards(self, orm):
        # Adding model 'Product'
        db.create_table(u'theimp_product', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('json', self.gf('django.db.models.fields.TextField')()),
            ('dropped', self.gf('django.db.models.fields.BooleanField')(default=False)),
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
            ('affiliate_identifier', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('comment', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('vendor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Vendor'], null=True, blank=True)),
        ))
        db.send_create_signal(u'theimp', ['Vendor'])

        # Adding model 'BrandMapping'
        db.create_table(u'theimp_brandmapping', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('vendor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['theimp.Vendor'])),
            ('brand', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('mapped_brand', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Brand'], null=True, blank=True)),
        ))
        db.send_create_signal(u'theimp', ['BrandMapping'])

        # Adding model 'CategoryMapping'
        db.create_table(u'theimp_categorymapping', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('vendor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['theimp.Vendor'])),
            ('category', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('mapped_category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Category'], null=True, blank=True)),
        ))
        db.send_create_signal(u'theimp', ['CategoryMapping'])

        # Adding model 'Mapping'
        db.create_table(u'theimp_mapping', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('mapping_type', self.gf('django.db.models.fields.CharField')(max_length=24)),
            ('mapping_key', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('mapping_aliases', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'theimp', ['Mapping'])


    def backwards(self, orm):
        # Deleting model 'Product'
        db.delete_table(u'theimp_product')

        # Deleting model 'Vendor'
        db.delete_table(u'theimp_vendor')

        # Deleting model 'BrandMapping'
        db.delete_table(u'theimp_brandmapping')

        # Deleting model 'CategoryMapping'
        db.delete_table(u'theimp_categorymapping')

        # Deleting model 'Mapping'
        db.delete_table(u'theimp_mapping')


    models = {
        u'apparel.brand': {
            'Meta': {'ordering': "['name']", 'object_name': 'Brand'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'old_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        },
        u'apparel.category': {
            'Meta': {'ordering': "('tree_id', 'lft')", 'object_name': 'Category'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'name_da': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'name_en': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'name_no': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'name_order': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name_order_da': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name_order_en': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name_order_no': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name_order_sv': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name_sv': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'on_front_page': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'option_types': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['apparel.OptionType']", 'symmetrical': 'False', 'blank': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': u"orm['apparel.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'singular_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'singular_name_da': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'singular_name_en': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'singular_name_no': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'singular_name_sv': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        u'apparel.optiontype': {
            'Meta': {'ordering': "['name']", 'object_name': 'OptionType'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': u"orm['apparel.OptionType']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        u'apparel.vendor': {
            'Meta': {'ordering': "['name']", 'object_name': 'Vendor'},
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logotype': ('django.db.models.fields.files.ImageField', [], {'max_length': '127', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'})
        },
        u'theimp.brandmapping': {
            'Meta': {'object_name': 'BrandMapping'},
            'brand': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mapped_brand': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['apparel.Brand']", 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['theimp.Vendor']"})
        },
        u'theimp.categorymapping': {
            'Meta': {'object_name': 'CategoryMapping'},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mapped_category': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['apparel.Category']", 'null': 'True', 'blank': 'True'}),
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
            'comment': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['apparel.Vendor']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['theimp']
