# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Product.product'
        db.add_column(u'theimp_product', 'product',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Product'], null=True, blank=True),
                      keep_default=False)

        # Adding index on 'Product', fields ['key']
        db.create_index(u'theimp_product', ['key'])


    def backwards(self, orm):
        # Removing index on 'Product', fields ['key']
        db.delete_index(u'theimp_product', ['key'])

        # Deleting field 'Product.product'
        db.delete_column(u'theimp_product', 'product_id')


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
            'name_da': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name_en': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name_fi': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name_no': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name_order': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name_order_da': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name_order_en': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name_order_fi': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name_order_no': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name_order_sv': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name_sv': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'on_front_page': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'option_types': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['apparel.OptionType']", 'symmetrical': 'False', 'blank': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': u"orm['apparel.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'singular_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'singular_name_da': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'singular_name_en': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'singular_name_fi': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'singular_name_no': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'singular_name_sv': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        u'apparel.location': {
            'Meta': {'ordering': "['code']", 'object_name': 'Location'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '3', 'primary_key': 'True'})
        },
        u'apparel.option': {
            'Meta': {'ordering': "['option_type']", 'unique_together': "(('option_type', 'value'),)", 'object_name': 'Option'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'option_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['apparel.OptionType']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'})
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
        u'apparel.product': {
            'Meta': {'ordering': "('-id',)", 'unique_together': "(('static_brand', 'sku'),)", 'object_name': 'Product'},
            'availability': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'category': ('mptt.fields.TreeForeignKey', [], {'to': u"orm['apparel.Category']", 'null': 'True', 'blank': 'True'}),
            'date_added': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'date_published': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'feed_gender': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'gender': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '1', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'manufacturer': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'products'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['apparel.Brand']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'options': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['apparel.Option']", 'symmetrical': 'False', 'blank': 'True'}),
            'popularity': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '20', 'decimal_places': '8', 'db_index': 'True'}),
            'product_image': (u'sorl.thumbnail.fields.ImageField', [], {'max_length': '255'}),
            'product_key': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'product_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'sku': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'slug': ('django_extensions.db.fields.AutoSlugField', [], {'allow_duplicates': 'False', 'max_length': '80', 'separator': "u'-'", 'blank': 'True', 'populate_from': "('static_brand', 'product_name')", 'overwrite': 'False'}),
            'static_brand': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'vendors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['apparel.Vendor']", 'through': u"orm['apparel.VendorProduct']", 'symmetrical': 'False'})
        },
        u'apparel.vendor': {
            'Meta': {'ordering': "['name']", 'object_name': 'Vendor'},
            'clicks_limit': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_cpc': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'is_cpo': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'is_limit_reached': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'locations': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['apparel.Location']", 'symmetrical': 'False'}),
            'logotype': ('django.db.models.fields.files.ImageField', [], {'max_length': '127', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['profile.User']"})
        },
        u'apparel.vendorbrand': {
            'Meta': {'ordering': "['name']", 'object_name': 'VendorBrand'},
            'brand': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'vendor_brands'", 'null': 'True', 'to': u"orm['apparel.Brand']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vendor_brands'", 'to': u"orm['apparel.Vendor']"})
        },
        u'apparel.vendorcategory': {
            'Meta': {'ordering': "['name']", 'object_name': 'VendorCategory'},
            'category': ('mptt.fields.TreeForeignKey', [], {'to': u"orm['apparel.Category']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'default_gender': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '555'}),
            'override_gender': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['apparel.Vendor']"})
        },
        u'apparel.vendorproduct': {
            'Meta': {'ordering': "['vendor', 'product']", 'object_name': 'VendorProduct'},
            '_original_discount_price': ('django.db.models.fields.DecimalField', [], {'blank': 'True', 'null': 'True', 'db_column': "'original_discount_price'", 'decimal_places': '2', 'max_digits': '10'}),
            '_original_price': ('django.db.models.fields.DecimalField', [], {'blank': 'True', 'null': 'True', 'db_column': "'original_price'", 'decimal_places': '2', 'max_digits': '10'}),
            'availability': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'buy_url': ('django.db.models.fields.URLField', [], {'max_length': '555', 'null': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True', 'blank': 'True'}),
            'discount_currency': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True', 'blank': 'True'}),
            'discount_price': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'original_currency': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True', 'blank': 'True'}),
            'original_discount_currency': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True', 'blank': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'db_index': 'True', 'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vendorproduct'", 'to': u"orm['apparel.Product']"}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['apparel.Vendor']"}),
            'vendor_brand': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vendor_products'", 'null': 'True', 'to': u"orm['apparel.VendorBrand']"}),
            'vendor_category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vendor_products'", 'null': 'True', 'to': u"orm['apparel.VendorCategory']"})
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
            'has_cpc_all_stores': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_subscriber': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owner_group'", 'null': 'True', 'to': u"orm['profile.User']"}),
            'owner_cut': ('django.db.models.fields.DecimalField', [], {'default': "'1.00'", 'null': 'True', 'max_digits': '10', 'decimal_places': '3', 'blank': 'True'})
        },
        u'profile.user': {
            'Meta': {'object_name': 'User'},
            'about': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'blog_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'brand': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'user'", 'unique': 'True', 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': u"orm['apparel.Brand']", 'blank': 'True', 'null': 'True'}),
            'brand_summaries': ('django.db.models.fields.CharField', [], {'default': "'W'", 'max_length': '1'}),
            'comment_look_comment': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'comment_look_created': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'comment_product_comment': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'comment_product_wardrobe': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'confirmation_key': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'discount_notification': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'earning_summaries': ('django.db.models.fields.CharField', [], {'default': "'D'", 'max_length': '1'}),
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
            'follow_recommendations': ('django.db.models.fields.CharField', [], {'default': "'W'", 'max_length': '1'}),
            'follow_user': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'followers_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'friend_summaries': ('django.db.models.fields.CharField', [], {'default': "'W'", 'max_length': '1'}),
            'gender': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_brand': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_partner': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_subscriber': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_top_partner': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "'en'", 'max_length': '10'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'like_look_created': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'login_flow': ('django.db.models.fields.CharField', [], {'default': "'complete'", 'max_length': '20'}),
            'look_like_summaries': ('django.db.models.fields.CharField', [], {'default': "'D'", 'max_length': '1'}),
            'manual_about': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'manual_about_da': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'manual_about_en': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'manual_about_fi': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'manual_about_no': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'manual_about_sv': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'owner_network': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'publisher_network'", 'null': 'True', 'to': u"orm['profile.User']"}),
            'owner_network_cut': ('django.db.models.fields.DecimalField', [], {'default': "'1.00'", 'null': 'True', 'max_digits': '10', 'decimal_places': '3', 'blank': 'True'}),
            'partner_group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dashboard.Group']", 'null': 'True', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'popularity': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '20', 'decimal_places': '8', 'db_index': 'True'}),
            'popularity_men': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '20', 'decimal_places': '8'}),
            'product_like_summaries': ('django.db.models.fields.CharField', [], {'default': "'D'", 'max_length': '1'}),
            'referral_partner': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'referral_partner_code': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'referral_partner_parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['profile.User']", 'null': 'True', 'blank': 'True'}),
            'referral_partner_parent_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'show_warnings': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '100', 'unique': 'True', 'null': 'True'}),
            'summary_mails': ('django.db.models.fields.CharField', [], {'default': "'W'", 'max_length': '1'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
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
            'mapped_category': ('mptt.fields.TreeForeignKey', [], {'to': u"orm['apparel.Category']", 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'products_counter': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
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
            'brand_mapping': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'products'", 'null': 'True', 'to': u"orm['theimp.BrandMapping']"}),
            'category_mapping': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'products'", 'null': 'True', 'to': u"orm['theimp.CategoryMapping']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imported_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'is_dropped': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_released': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_validated': ('django.db.models.fields.NullBooleanField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'json': ('django.db.models.fields.TextField', [], {}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '512', 'db_index': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'parsed_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['apparel.Product']", 'null': 'True', 'blank': 'True'}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['theimp.Vendor']"})
        },
        u'theimp.vendor': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Vendor'},
            'affiliate_identifier': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'comment': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_imported_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['apparel.Vendor']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['theimp']