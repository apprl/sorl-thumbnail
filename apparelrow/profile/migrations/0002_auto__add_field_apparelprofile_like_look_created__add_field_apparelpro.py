# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding field 'ApparelProfile.like_look_created'
        db.add_column('profile_apparelprofile', 'like_look_created', self.gf('django.db.models.fields.CharField')(default='F', max_length=1), keep_default=False)

        # Adding field 'ApparelProfile.follow_user'
        db.add_column('profile_apparelprofile', 'follow_user', self.gf('django.db.models.fields.CharField')(default='F', max_length=1), keep_default=False)

        # Adding field 'ApparelProfile.comment_product_comment'
        db.add_column('profile_apparelprofile', 'comment_product_comment', self.gf('django.db.models.fields.CharField')(default='F', max_length=1), keep_default=False)

        # Adding field 'ApparelProfile.comment_look_created'
        db.add_column('profile_apparelprofile', 'comment_look_created', self.gf('django.db.models.fields.CharField')(default='F', max_length=1), keep_default=False)

        # Adding field 'ApparelProfile.comment_product_wardrobe'
        db.add_column('profile_apparelprofile', 'comment_product_wardrobe', self.gf('django.db.models.fields.CharField')(default='F', max_length=1), keep_default=False)

        # Adding field 'ApparelProfile.comment_look_comment'
        db.add_column('profile_apparelprofile', 'comment_look_comment', self.gf('django.db.models.fields.CharField')(default='F', max_length=1), keep_default=False)
    
    
    def backwards(self, orm):
        
        # Deleting field 'ApparelProfile.like_look_created'
        db.delete_column('profile_apparelprofile', 'like_look_created')

        # Deleting field 'ApparelProfile.follow_user'
        db.delete_column('profile_apparelprofile', 'follow_user')

        # Deleting field 'ApparelProfile.comment_product_comment'
        db.delete_column('profile_apparelprofile', 'comment_product_comment')

        # Deleting field 'ApparelProfile.comment_look_created'
        db.delete_column('profile_apparelprofile', 'comment_look_created')

        # Deleting field 'ApparelProfile.comment_product_wardrobe'
        db.delete_column('profile_apparelprofile', 'comment_product_wardrobe')

        # Deleting field 'ApparelProfile.comment_look_comment'
        db.delete_column('profile_apparelprofile', 'comment_look_comment')
    
    
    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'profile.apparelprofile': {
            'Meta': {'object_name': 'ApparelProfile'},
            'about': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'comment_look_comment': ('django.db.models.fields.CharField', [], {'default': "'F'", 'max_length': '1'}),
            'comment_look_created': ('django.db.models.fields.CharField', [], {'default': "'F'", 'max_length': '1'}),
            'comment_product_comment': ('django.db.models.fields.CharField', [], {'default': "'F'", 'max_length': '1'}),
            'comment_product_wardrobe': ('django.db.models.fields.CharField', [], {'default': "'F'", 'max_length': '1'}),
            'follow_user': ('django.db.models.fields.CharField', [], {'default': "'F'", 'max_length': '1'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'like_look_created': ('django.db.models.fields.CharField', [], {'default': "'F'", 'max_length': '1'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }
    
    complete_apps = ['profile']
