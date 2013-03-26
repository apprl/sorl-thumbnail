# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Transaction'
        db.create_table(u'affiliate_transaction', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('store_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('order_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('order_value', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=12, decimal_places=2)),
            ('currency', self.gf('django.db.models.fields.CharField')(default='SEK', max_length=3)),
            ('cookie_date', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, null=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, null=True, blank=True)),
            ('ip_address', self.gf('django.db.models.fields.GenericIPAddressField')(max_length=39)),
            ('status', self.gf('django.db.models.fields.CharField')(default='P', max_length=1)),
            ('status_message', self.gf('django.db.models.fields.TextField')(default='')),
        ))
        db.send_create_signal(u'affiliate', ['Transaction'])


    def backwards(self, orm):
        # Deleting model 'Transaction'
        db.delete_table(u'affiliate_transaction')


    models = {
        u'affiliate.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'cookie_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'default': "'SEK'", 'max_length': '3'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'order_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'order_value': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '12', 'decimal_places': '2'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'P'", 'max_length': '1'}),
            'status_message': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'store_id': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        }
    }

    complete_apps = ['affiliate']