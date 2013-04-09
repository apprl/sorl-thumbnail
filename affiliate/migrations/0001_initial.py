# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    depends_on = (
        ('profile', '0002_auto__add_field_user_brand__add_field_user_partner_group'),
    )

    def forwards(self, orm):
        # Adding model 'Store'
        db.create_table(u'affiliate_store', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('identifier', self.gf('django.db.models.fields.CharField')(unique=True, max_length=64)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='affiliate_store', unique=True, on_delete=models.SET_NULL, default=None, to=orm['profile.User'], blank=True, null=True)),
            ('balance', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=12, decimal_places=2)),
            ('commission_percentage', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=12, decimal_places=2)),
            ('cookie_days', self.gf('django.db.models.fields.PositiveIntegerField')(default=30)),
            ('vendor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Vendor'])),
        ))
        db.send_create_signal(u'affiliate', ['Store'])

        # Adding model 'StoreHistory'
        db.create_table(u'affiliate_storehistory', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('store', self.gf('django.db.models.fields.related.ForeignKey')(related_name='history', to=orm['affiliate.Store'])),
            ('balance', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=12, decimal_places=2)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, null=True, blank=True)),
        ))
        db.send_create_signal(u'affiliate', ['StoreHistory'])

        # Adding model 'Product'
        db.create_table(u'affiliate_product', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('transaction', self.gf('django.db.models.fields.related.ForeignKey')(related_name='products', to=orm['affiliate.Transaction'])),
            ('sku', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('price', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=12, decimal_places=2)),
            ('quantity', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
        ))
        db.send_create_signal(u'affiliate', ['Product'])

        # Adding model 'Transaction'
        db.create_table(u'affiliate_transaction', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('store_id', self.gf('django.db.models.fields.CharField')(max_length=64, db_index=True)),
            ('order_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('order_value', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=12, decimal_places=2)),
            ('currency', self.gf('django.db.models.fields.CharField')(default='SEK', max_length=3)),
            ('commission', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=12, decimal_places=2)),
            ('cookie_date', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, null=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, null=True, blank=True)),
            ('custom', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('ip_address', self.gf('django.db.models.fields.GenericIPAddressField')(max_length=39)),
            ('status', self.gf('django.db.models.fields.CharField')(default='P', max_length=1)),
            ('status_message', self.gf('django.db.models.fields.TextField')(default='', null=True, blank=True)),
            ('status_date', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True, blank=True)),
        ))
        db.send_create_signal(u'affiliate', ['Transaction'])

        # Adding model 'Cookie'
        db.create_table(u'affiliate_cookie', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('cookie_id', self.gf('django.db.models.fields.CharField')(max_length=32, db_index=True)),
            ('store_id', self.gf('django.db.models.fields.CharField')(max_length=128, db_index=True)),
            ('old_cookie_id', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('custom', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal(u'affiliate', ['Cookie'])


    def backwards(self, orm):
        # Deleting model 'Store'
        db.delete_table(u'affiliate_store')

        # Deleting model 'StoreHistory'
        db.delete_table(u'affiliate_storehistory')

        # Deleting model 'Product'
        db.delete_table(u'affiliate_product')

        # Deleting model 'Transaction'
        db.delete_table(u'affiliate_transaction')

        # Deleting model 'Cookie'
        db.delete_table(u'affiliate_cookie')


    models = {
        u'affiliate.cookie': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Cookie'},
            'cookie_id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'db_index': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'custom': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'old_cookie_id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'store_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'})
        },
        u'affiliate.product': {
            'Meta': {'object_name': 'Product'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '12', 'decimal_places': '2'}),
            'quantity': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'sku': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'transaction': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'products'", 'to': u"orm['affiliate.Transaction']"})
        },
        u'affiliate.store': {
            'Meta': {'object_name': 'Store'},
            'balance': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '12', 'decimal_places': '2'}),
            'commission_percentage': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '12', 'decimal_places': '2'}),
            'cookie_days': ('django.db.models.fields.PositiveIntegerField', [], {'default': '30'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'affiliate_store'", 'unique': 'True', 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': u"orm['profile.User']", 'blank': 'True', 'null': 'True'}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['apparel.Vendor']"})
        },
        u'affiliate.storehistory': {
            'Meta': {'ordering': "['-created']", 'object_name': 'StoreHistory'},
            'balance': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '12', 'decimal_places': '2'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'store': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'history'", 'to': u"orm['affiliate.Store']"})
        },
        u'affiliate.transaction': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Transaction'},
            'commission': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '12', 'decimal_places': '2'}),
            'cookie_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'default': "'SEK'", 'max_length': '3'}),
            'custom': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'order_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'order_value': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '12', 'decimal_places': '2'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'P'", 'max_length': '1'}),
            'status_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'status_message': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'store_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'})
        },
        u'apparel.brand': {
            'Meta': {'ordering': "['name']", 'object_name': 'Brand'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'old_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        },
        u'apparel.vendor': {
            'Meta': {'ordering': "['name']", 'object_name': 'Vendor'},
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logotype': ('django.db.models.fields.files.ImageField', [], {'max_length': '127', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'dashboard.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        u'profile.user': {
            'Meta': {'object_name': 'User'},
            'about': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'blog_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'brand': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'user'", 'unique': 'True', 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': u"orm['apparel.Brand']", 'blank': 'True', 'null': 'True'}),
            'comment_look_comment': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'comment_look_created': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'comment_product_comment': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'comment_product_wardrobe': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'confirmation_key': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'discount_notification': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'facebook_access_token': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'facebook_access_token_expire': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'facebook_friends': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'facebook_user_id': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '30', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'fb_share_create_look': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'fb_share_follow_profile': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'fb_share_like_look': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'fb_share_like_product': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'follow_user': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'followers_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'gender': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_brand': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_partner': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "'sv'", 'max_length': '10'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'like_look_created': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'login_flow': ('django.db.models.fields.CharField', [], {'default': "'friends'", 'max_length': '20'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'partner_group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dashboard.Group']", 'null': 'True', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'popularity': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '20', 'decimal_places': '8', 'db_index': 'True'}),
            'popularity_men': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '20', 'decimal_places': '8'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '100', 'unique': 'True', 'null': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        }
    }

    complete_apps = ['affiliate']
