# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Group.is_subscriber'
        db.add_column(u'dashboard_group', 'is_subscriber',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Group.is_subscriber'
        db.delete_column(u'dashboard_group', 'is_subscriber')


    models = {
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
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['profile.User']"})
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
        u'dashboard.cut': {
            'Meta': {'object_name': 'Cut'},
            'cut': ('django.db.models.fields.DecimalField', [], {'default': "'0.67'", 'max_digits': '10', 'decimal_places': '3'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cuts'", 'on_delete': 'models.PROTECT', 'to': u"orm['dashboard.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'referral_cut': ('django.db.models.fields.DecimalField', [], {'default': "'0.33'", 'max_digits': '10', 'decimal_places': '3'}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['apparel.Vendor']"})
        },
        u'dashboard.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_subscriber': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owner_group'", 'null': 'True', 'to': u"orm['profile.User']"}),
            'owner_cut': ('django.db.models.fields.DecimalField', [], {'default': "'1.00'", 'null': 'True', 'max_digits': '10', 'decimal_places': '3', 'blank': 'True'})
        },
        u'dashboard.payment': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'Payment'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '10', 'decimal_places': '2'}),
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'default': "'EUR'", 'max_length': '3'}),
            'details': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['profile.PaymentDetail']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'paid': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['profile.User']"})
        },
        u'dashboard.sale': {
            'Meta': {'ordering': "['-sale_date']", 'object_name': 'Sale'},
            'adjusted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'adjusted_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'affiliate': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '10', 'decimal_places': '2'}),
            'commission': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '10', 'decimal_places': '2'}),
            'converted_amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '10', 'decimal_places': '2'}),
            'converted_commission': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '10', 'decimal_places': '2'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'default': "'EUR'", 'max_length': '3'}),
            'cut': ('django.db.models.fields.DecimalField', [], {'default': "'1.0'", 'max_digits': '10', 'decimal_places': '3'}),
            'exchange_rate': ('django.db.models.fields.DecimalField', [], {'default': "'1'", 'max_digits': '10', 'decimal_places': '6'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_promo': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_referral_sale': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'original_amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '10', 'decimal_places': '2'}),
            'original_commission': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '10', 'decimal_places': '2'}),
            'original_currency': ('django.db.models.fields.CharField', [], {'default': "'EUR'", 'max_length': '3'}),
            'original_sale_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'paid': ('django.db.models.fields.CharField', [], {'default': "'0'", 'max_length': '1'}),
            'placement': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'product_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'quantity': ('django.db.models.fields.PositiveIntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'referral_user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['profile.User']", 'null': 'True', 'blank': 'True'}),
            'sale_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'0'", 'max_length': '1', 'db_index': 'True'}),
            'user_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['apparel.Vendor']", 'null': 'True', 'on_delete': 'models.PROTECT', 'blank': 'True'})
        },
        u'dashboard.signup': {
            'Meta': {'object_name': 'Signup'},
            'blog': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referral_user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['profile.User']", 'null': 'True', 'blank': 'True'}),
            'store': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'dashboard.storecommission': {
            'Meta': {'object_name': 'StoreCommission'},
            'commission': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['apparel.Vendor']"})
        },
        u'profile.paymentdetail': {
            'Meta': {'object_name': 'PaymentDetail'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'banknr': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'clearingnr': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'company': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'orgnr': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'postal_code': ('django.db.models.fields.CharField', [], {'max_length': '8', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['profile.User']"})
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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_brand': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_partner': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_top_partner': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "'en'", 'max_length': '10'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'like_look_created': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'login_flow': ('django.db.models.fields.CharField', [], {'default': "'complete'", 'max_length': '20'}),
            'manual_about': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'manual_about_da': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'manual_about_en': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'manual_about_no': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'manual_about_sv': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'partner_group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dashboard.Group']", 'null': 'True', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'popularity': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '20', 'decimal_places': '8', 'db_index': 'True'}),
            'popularity_men': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '20', 'decimal_places': '8'}),
            'referral_partner': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'referral_partner_code': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'referral_partner_parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['profile.User']", 'null': 'True', 'blank': 'True'}),
            'referral_partner_parent_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '100', 'unique': 'True', 'null': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        }
    }

    complete_apps = ['dashboard']