# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'User.name'
        db.add_column('profile_user', 'name',
                      self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True),
                      keep_default=False)

        # Adding field 'User.slug'
        db.add_column('profile_user', 'slug',
                      self.gf('django.db.models.fields.CharField')(max_length=100, unique=True, null=True),
                      keep_default=False)

        # Adding field 'User.image'
        db.add_column('profile_user', 'image',
                      self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True),
                      keep_default=False)

        # Adding field 'User.about'
        db.add_column('profile_user', 'about',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'User.language'
        db.add_column('profile_user', 'language',
                      self.gf('django.db.models.fields.CharField')(default='sv', max_length=10),
                      keep_default=False)

        # Adding field 'User.gender'
        db.add_column('profile_user', 'gender',
                      self.gf('django.db.models.fields.CharField')(default=None, max_length=1, null=True, blank=True),
                      keep_default=False)

        # Adding field 'User.blog_url'
        db.add_column('profile_user', 'blog_url',
                      self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True),
                      keep_default=False)

        # Adding field 'User.is_brand'
        db.add_column('profile_user', 'is_brand',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'User.brand'
        db.add_column('profile_user', 'brand',
                      self.gf('django.db.models.fields.related.OneToOneField')(related_name='user', unique=True, on_delete=models.SET_NULL, default=None, to=orm['apparel.Brand'], blank=True, null=True),
                      keep_default=False)

        # Adding field 'User.login_flow'
        db.add_column('profile_user', 'login_flow',
                      self.gf('django.db.models.fields.CharField')(default='bio', max_length=20),
                      keep_default=False)

        # Adding field 'User.newsletter'
        db.add_column('profile_user', 'newsletter',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)

        # Adding field 'User.discount_notification'
        db.add_column('profile_user', 'discount_notification',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)

        # Adding field 'User.fb_share_like_product'
        db.add_column('profile_user', 'fb_share_like_product',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)

        # Adding field 'User.fb_share_like_look'
        db.add_column('profile_user', 'fb_share_like_look',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)

        # Adding field 'User.fb_share_follow_profile'
        db.add_column('profile_user', 'fb_share_follow_profile',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)

        # Adding field 'User.fb_share_create_look'
        db.add_column('profile_user', 'fb_share_create_look',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)

        # Adding field 'User.facebook_access_token'
        db.add_column('profile_user', 'facebook_access_token',
                      self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True),
                      keep_default=False)

        # Adding field 'User.facebook_access_token_expire'
        db.add_column('profile_user', 'facebook_access_token_expire',
                      self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'User.is_partner'
        db.add_column('profile_user', 'is_partner',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'User.partner_group'
        db.add_column('profile_user', 'partner_group',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['dashboard.Group'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'User.comment_product_wardrobe'
        db.add_column('profile_user', 'comment_product_wardrobe',
                      self.gf('django.db.models.fields.CharField')(default='A', max_length=1),
                      keep_default=False)

        # Adding field 'User.comment_product_comment'
        db.add_column('profile_user', 'comment_product_comment',
                      self.gf('django.db.models.fields.CharField')(default='A', max_length=1),
                      keep_default=False)

        # Adding field 'User.comment_look_created'
        db.add_column('profile_user', 'comment_look_created',
                      self.gf('django.db.models.fields.CharField')(default='A', max_length=1),
                      keep_default=False)

        # Adding field 'User.comment_look_comment'
        db.add_column('profile_user', 'comment_look_comment',
                      self.gf('django.db.models.fields.CharField')(default='A', max_length=1),
                      keep_default=False)

        # Adding field 'User.like_look_created'
        db.add_column('profile_user', 'like_look_created',
                      self.gf('django.db.models.fields.CharField')(default='A', max_length=1),
                      keep_default=False)

        # Adding field 'User.follow_user'
        db.add_column('profile_user', 'follow_user',
                      self.gf('django.db.models.fields.CharField')(default='A', max_length=1),
                      keep_default=False)

        # Adding field 'User.facebook_friends'
        db.add_column('profile_user', 'facebook_friends',
                      self.gf('django.db.models.fields.CharField')(default='A', max_length=1),
                      keep_default=False)

        # Adding field 'User.followers_count'
        db.add_column('profile_user', 'followers_count',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)

        # Adding field 'User.popularity'
        db.add_column('profile_user', 'popularity',
                      self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=20, decimal_places=8, db_index=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'User.name'
        db.delete_column('profile_user', 'name')

        # Deleting field 'User.slug'
        db.delete_column('profile_user', 'slug')

        # Deleting field 'User.image'
        db.delete_column('profile_user', 'image')

        # Deleting field 'User.about'
        db.delete_column('profile_user', 'about')

        # Deleting field 'User.language'
        db.delete_column('profile_user', 'language')

        # Deleting field 'User.gender'
        db.delete_column('profile_user', 'gender')

        # Deleting field 'User.blog_url'
        db.delete_column('profile_user', 'blog_url')

        # Deleting field 'User.is_brand'
        db.delete_column('profile_user', 'is_brand')

        # Deleting field 'User.brand'
        db.delete_column('profile_user', 'brand_id')

        # Deleting field 'User.login_flow'
        db.delete_column('profile_user', 'login_flow')

        # Deleting field 'User.newsletter'
        db.delete_column('profile_user', 'newsletter')

        # Deleting field 'User.discount_notification'
        db.delete_column('profile_user', 'discount_notification')

        # Deleting field 'User.fb_share_like_product'
        db.delete_column('profile_user', 'fb_share_like_product')

        # Deleting field 'User.fb_share_like_look'
        db.delete_column('profile_user', 'fb_share_like_look')

        # Deleting field 'User.fb_share_follow_profile'
        db.delete_column('profile_user', 'fb_share_follow_profile')

        # Deleting field 'User.fb_share_create_look'
        db.delete_column('profile_user', 'fb_share_create_look')

        # Deleting field 'User.facebook_access_token'
        db.delete_column('profile_user', 'facebook_access_token')

        # Deleting field 'User.facebook_access_token_expire'
        db.delete_column('profile_user', 'facebook_access_token_expire')

        # Deleting field 'User.is_partner'
        db.delete_column('profile_user', 'is_partner')

        # Deleting field 'User.partner_group'
        db.delete_column('profile_user', 'partner_group_id')

        # Deleting field 'User.comment_product_wardrobe'
        db.delete_column('profile_user', 'comment_product_wardrobe')

        # Deleting field 'User.comment_product_comment'
        db.delete_column('profile_user', 'comment_product_comment')

        # Deleting field 'User.comment_look_created'
        db.delete_column('profile_user', 'comment_look_created')

        # Deleting field 'User.comment_look_comment'
        db.delete_column('profile_user', 'comment_look_comment')

        # Deleting field 'User.like_look_created'
        db.delete_column('profile_user', 'like_look_created')

        # Deleting field 'User.follow_user'
        db.delete_column('profile_user', 'follow_user')

        # Deleting field 'User.facebook_friends'
        db.delete_column('profile_user', 'facebook_friends')

        # Deleting field 'User.followers_count'
        db.delete_column('profile_user', 'followers_count')

        # Deleting field 'User.popularity'
        db.delete_column('profile_user', 'popularity')


    models = {
        u'apparel.brand': {
            'Meta': {'ordering': "['name']", 'object_name': 'Brand'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'old_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
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
        u'profile.apparelprofile': {
            'Meta': {'object_name': 'ApparelProfile'},
            'about': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'blog_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'brand': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'profile'", 'unique': 'True', 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': u"orm['apparel.Brand']", 'blank': 'True', 'null': 'True'}),
            'comment_look_comment': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'comment_look_created': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'comment_product_comment': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'comment_product_wardrobe': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'discount_notification': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'facebook_access_token': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'facebook_access_token_expire': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'facebook_friends': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'fb_share_create_look': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'fb_share_follow_profile': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'fb_share_like_look': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'fb_share_like_product': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'first_visit': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'follow_user': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'followers_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'gender': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '1', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'is_brand': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_partner': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "'sv'", 'max_length': '10'}),
            'like_look_created': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
            'login_flow': ('django.db.models.fields.CharField', [], {'default': "'bio'", 'max_length': '20'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'partner_group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dashboard.Group']", 'null': 'True', 'blank': 'True'}),
            'popularity': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '20', 'decimal_places': '8', 'db_index': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '100', 'unique': 'True', 'null': 'True'}),
            'updates_last_visit': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'profile'", 'unique': 'True', 'to': u"orm['profile.User']"})
        },
        u'profile.emailchange': {
            'Meta': {'object_name': 'EmailChange'},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '42'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['profile.User']"})
        },
        u'profile.follow': {
            'Meta': {'unique_together': "(('user', 'user_follow'),)", 'object_name': 'Follow'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'following'", 'to': u"orm['profile.ApparelProfile']"}),
            'user_follow': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'followers'", 'to': u"orm['profile.ApparelProfile']"})
        },
        u'profile.notificationcache': {
            'Meta': {'object_name': 'NotificationCache'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
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
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'discount_notification': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'facebook_access_token': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'facebook_access_token_expire': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'facebook_friends': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '1'}),
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
            'login_flow': ('django.db.models.fields.CharField', [], {'default': "'bio'", 'max_length': '20'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'partner_group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dashboard.Group']", 'null': 'True', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'popularity': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '20', 'decimal_places': '8', 'db_index': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '100', 'unique': 'True', 'null': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        }
    }

    complete_apps = ['profile']