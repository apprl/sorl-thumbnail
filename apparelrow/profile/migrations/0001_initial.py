# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'User'
        db.create_table('profile_user', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('last_login', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('is_superuser', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('username', self.gf('django.db.models.fields.CharField')(unique=True, max_length=30)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
            ('is_staff', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('date_joined', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.CharField')(max_length=100, unique=True, null=True)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('about', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('language', self.gf('django.db.models.fields.CharField')(default='sv', max_length=10)),
            ('gender', self.gf('django.db.models.fields.CharField')(default=None, max_length=1, null=True, blank=True)),
            ('blog_url', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('is_brand', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('brand', self.gf('django.db.models.fields.related.OneToOneField')(related_name='user', unique=True, on_delete=models.SET_NULL, default=None, to=orm['apparel.Brand'], blank=True, null=True)),
            ('confirmation_key', self.gf('django.db.models.fields.CharField')(default=None, max_length=32, null=True, blank=True)),
            ('login_flow', self.gf('django.db.models.fields.CharField')(default='friends', max_length=20)),
            ('newsletter', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('discount_notification', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('fb_share_like_product', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('fb_share_like_look', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('fb_share_follow_profile', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('fb_share_create_look', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('facebook_user_id', self.gf('django.db.models.fields.CharField')(default=None, max_length=30, unique=True, null=True, blank=True)),
            ('facebook_access_token', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('facebook_access_token_expire', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('is_partner', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('partner_group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['dashboard.Group'], null=True, blank=True)),
            ('comment_product_wardrobe', self.gf('django.db.models.fields.CharField')(default='A', max_length=1)),
            ('comment_product_comment', self.gf('django.db.models.fields.CharField')(default='A', max_length=1)),
            ('comment_look_created', self.gf('django.db.models.fields.CharField')(default='A', max_length=1)),
            ('comment_look_comment', self.gf('django.db.models.fields.CharField')(default='A', max_length=1)),
            ('like_look_created', self.gf('django.db.models.fields.CharField')(default='A', max_length=1)),
            ('follow_user', self.gf('django.db.models.fields.CharField')(default='A', max_length=1)),
            ('facebook_friends', self.gf('django.db.models.fields.CharField')(default='A', max_length=1)),
            ('followers_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('popularity', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=20, decimal_places=8, db_index=True)),
            ('popularity_men', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=20, decimal_places=8)),
        ))
        db.send_create_signal(u'profile', ['User'])

        # Adding M2M table for field groups on 'User'
        db.create_table('profile_user_groups', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('user', models.ForeignKey(orm[u'profile.user'], null=False)),
            ('group', models.ForeignKey(orm[u'auth.group'], null=False))
        ))
        db.create_unique('profile_user_groups', ['user_id', 'group_id'])

        # Adding M2M table for field user_permissions on 'User'
        db.create_table('profile_user_user_permissions', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('user', models.ForeignKey(orm[u'profile.user'], null=False)),
            ('permission', models.ForeignKey(orm[u'auth.permission'], null=False))
        ))
        db.create_unique('profile_user_user_permissions', ['user_id', 'permission_id'])

        # Adding model 'PaymentDetail'
        db.create_table(u'profile_paymentdetail', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['profile.User'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('company', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('orgnr', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('banknr', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('clearingnr', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('postal_code', self.gf('django.db.models.fields.CharField')(max_length=8, null=True, blank=True)),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
        ))
        db.send_create_signal(u'profile', ['PaymentDetail'])

        # Adding model 'EmailChange'
        db.create_table(u'profile_emailchange', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['profile.User'])),
            ('token', self.gf('django.db.models.fields.CharField')(max_length=42)),
            ('email', self.gf('django.db.models.fields.CharField')(max_length=256)),
        ))
        db.send_create_signal(u'profile', ['EmailChange'])

        # Adding model 'Follow'
        db.create_table(u'profile_follow', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='following', to=orm['profile.User'])),
            ('user_follow', self.gf('django.db.models.fields.related.ForeignKey')(related_name='followers', to=orm['profile.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True, db_index=True)),
        ))
        db.send_create_signal(u'profile', ['Follow'])

        # Adding unique constraint on 'Follow', fields ['user', 'user_follow']
        db.create_unique(u'profile_follow', ['user_id', 'user_follow_id'])

        # Adding model 'NotificationCache'
        db.create_table(u'profile_notificationcache', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('key', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
        ))
        db.send_create_signal(u'profile', ['NotificationCache'])


    def backwards(self, orm):
        # Removing unique constraint on 'Follow', fields ['user', 'user_follow']
        db.delete_unique(u'profile_follow', ['user_id', 'user_follow_id'])

        # Deleting model 'User'
        db.delete_table('profile_user')

        # Removing M2M table for field groups on 'User'
        db.delete_table('profile_user_groups')

        # Removing M2M table for field user_permissions on 'User'
        db.delete_table('profile_user_user_permissions')

        # Deleting model 'PaymentDetail'
        db.delete_table(u'profile_paymentdetail')

        # Deleting model 'EmailChange'
        db.delete_table(u'profile_emailchange')

        # Deleting model 'Follow'
        db.delete_table(u'profile_follow')

        # Deleting model 'NotificationCache'
        db.delete_table(u'profile_notificationcache')


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
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'following'", 'to': u"orm['profile.User']"}),
            'user_follow': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'followers'", 'to': u"orm['profile.User']"})
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

    complete_apps = ['profile']
