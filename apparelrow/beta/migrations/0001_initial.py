# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding model 'Invite'
        db.create_table('beta_invite', (
            ('code', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('beta', ['Invite'])

        # Adding model 'Invitee'
        db.create_table('beta_invitee', (
            ('seen', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('invite', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['beta.Invite'])),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
        ))
        db.send_create_signal('beta', ['Invitee'])
    
    
    def backwards(self, orm):
        
        # Deleting model 'Invite'
        db.delete_table('beta_invite')

        # Deleting model 'Invitee'
        db.delete_table('beta_invitee')
    
    
    models = {
        'beta.invite': {
            'Meta': {'object_name': 'Invite'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'beta.invitee': {
            'Meta': {'object_name': 'Invitee'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['beta.Invite']"}),
            'seen': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['beta']
