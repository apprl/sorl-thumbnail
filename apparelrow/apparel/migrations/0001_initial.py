# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding model 'Manufacturer'
        db.create_table('apparel_manufacturer', (
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('homepage', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('logotype', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
        ))
        db.send_create_signal('apparel', ['Manufacturer'])

        # Adding model 'OptionType'
        db.create_table('apparel_optiontype', (
            ('rght', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='children', null=True, to=orm['apparel.OptionType'])),
            ('level', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('lft', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('tree_id', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
        ))
        db.send_create_signal('apparel', ['OptionType'])

        # Adding model 'Option'
        db.create_table('apparel_option', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('option_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.OptionType'])),
        ))
        db.send_create_signal('apparel', ['Option'])

        # Adding unique constraint on 'Option', fields ['option_type', 'value']
        db.create_unique('apparel_option', ['option_type_id', 'value'])

        # Adding model 'Vendor'
        db.create_table('apparel_vendor', (
            ('logotype', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
            ('homepage', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('apparel', ['Vendor'])

        # Adding model 'Category'
        db.create_table('apparel_category', (
            ('rght', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='children', null=True, to=orm['apparel.Category'])),
            ('level', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('lft', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('key', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100, blank=True)),
            ('tree_id', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('apparel', ['Category'])

        # Adding M2M table for field option_types on 'Category'
        db.create_table('apparel_category_option_types', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('category', models.ForeignKey(orm['apparel.category'], null=False)),
            ('optiontype', models.ForeignKey(orm['apparel.optiontype'], null=False))
        ))
        db.create_unique('apparel_category_option_types', ['category_id', 'optiontype_id'])

        # Adding model 'CategoryAlias'
        db.create_table('apparel_categoryalias', (
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Category'])),
            ('alias', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('apparel', ['CategoryAlias'])

        # Adding model 'Product'
        db.create_table('apparel_product', (
            ('sku', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(db_index=True, max_length=80, blank=True)),
            ('product_image', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date_added', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('product_name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('manufacturer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Manufacturer'])),
        ))
        db.send_create_signal('apparel', ['Product'])

        # Adding M2M table for field category on 'Product'
        db.create_table('apparel_product_category', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('product', models.ForeignKey(orm['apparel.product'], null=False)),
            ('category', models.ForeignKey(orm['apparel.category'], null=False))
        ))
        db.create_unique('apparel_product_category', ['product_id', 'category_id'])

        # Adding M2M table for field options on 'Product'
        db.create_table('apparel_product_options', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('product', models.ForeignKey(orm['apparel.product'], null=False)),
            ('option', models.ForeignKey(orm['apparel.option'], null=False))
        ))
        db.create_unique('apparel_product_options', ['product_id', 'option_id'])

        # Adding model 'VendorProduct'
        db.create_table('apparel_vendorproduct', (
            ('product', self.gf('django.db.models.fields.related.ForeignKey')(related_name='vendorproduct', to=orm['apparel.Product'])),
            ('vendor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Vendor'])),
            ('price', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=10, decimal_places=2, blank=True)),
            ('currency', self.gf('django.db.models.fields.CharField')(max_length=3, null=True, blank=True)),
            ('buy_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('apparel', ['VendorProduct'])

        # Adding model 'Look'
        db.create_table('apparel_look', (
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('slug', self.gf('django.db.models.fields.SlugField')(db_index=True, max_length=80, blank=True)),
            ('tags', self.gf('tagging.fields.TagField')()),
        ))
        db.send_create_signal('apparel', ['Look'])

        # Adding model 'LookProduct'
        db.create_table('apparel_lookproduct', (
            ('product', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Product'])),
            ('z_index', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('look', self.gf('django.db.models.fields.related.ForeignKey')(related_name='look_products', to=orm['apparel.Look'])),
            ('top', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('height', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('width', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('left', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('apparel', ['LookProduct'])

        # Adding unique constraint on 'LookProduct', fields ['product', 'look']
        db.create_unique('apparel_lookproduct', ['product_id', 'look_id'])

        # Adding model 'Wardrobe'
        db.create_table('apparel_wardrobe', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('apparel', ['Wardrobe'])

        # Adding M2M table for field products on 'Wardrobe'
        db.create_table('apparel_wardrobe_products', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('wardrobe', models.ForeignKey(orm['apparel.wardrobe'], null=False)),
            ('product', models.ForeignKey(orm['apparel.product'], null=False))
        ))
        db.create_unique('apparel_wardrobe_products', ['wardrobe_id', 'product_id'])
    
    
    def backwards(self, orm):
        
        # Deleting model 'Manufacturer'
        db.delete_table('apparel_manufacturer')

        # Deleting model 'OptionType'
        db.delete_table('apparel_optiontype')

        # Deleting model 'Option'
        db.delete_table('apparel_option')

        # Removing unique constraint on 'Option', fields ['option_type', 'value']
        db.delete_unique('apparel_option', ['option_type_id', 'value'])

        # Deleting model 'Vendor'
        db.delete_table('apparel_vendor')

        # Deleting model 'Category'
        db.delete_table('apparel_category')

        # Removing M2M table for field option_types on 'Category'
        db.delete_table('apparel_category_option_types')

        # Deleting model 'CategoryAlias'
        db.delete_table('apparel_categoryalias')

        # Deleting model 'Product'
        db.delete_table('apparel_product')

        # Removing M2M table for field category on 'Product'
        db.delete_table('apparel_product_category')

        # Removing M2M table for field options on 'Product'
        db.delete_table('apparel_product_options')

        # Deleting model 'VendorProduct'
        db.delete_table('apparel_vendorproduct')

        # Deleting model 'Look'
        db.delete_table('apparel_look')

        # Deleting model 'LookProduct'
        db.delete_table('apparel_lookproduct')

        # Removing unique constraint on 'LookProduct', fields ['product', 'look']
        db.delete_unique('apparel_lookproduct', ['product_id', 'look_id'])

        # Deleting model 'Wardrobe'
        db.delete_table('apparel_wardrobe')

        # Removing M2M table for field products on 'Wardrobe'
        db.delete_table('apparel_wardrobe_products')
    
    
    models = {
        'apparel.category': {
            'Meta': {'object_name': 'Category'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'option_types': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['apparel.OptionType']", 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['apparel.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'apparel.categoryalias': {
            'Meta': {'object_name': 'CategoryAlias'},
            'alias': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'blank': 'True'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['apparel.Category']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'apparel.look': {
            'Meta': {'object_name': 'Look'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'products': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['apparel.Product']", 'through': "'LookProduct'"}),
            'slug': ('django.db.models.fields.SlugField', [], {'db_index': 'True', 'max_length': '80', 'blank': 'True'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'apparel.lookproduct': {
            'Meta': {'unique_together': "(('product', 'look'),)", 'object_name': 'LookProduct'},
            'height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'left': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'look': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'look_products'", 'to': "orm['apparel.Look']"}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['apparel.Product']"}),
            'top': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'z_index': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'apparel.manufacturer': {
            'Meta': {'object_name': 'Manufacturer'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logotype': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        },
        'apparel.option': {
            'Meta': {'unique_together': "(('option_type', 'value'),)", 'object_name': 'Option'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'option_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['apparel.OptionType']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'apparel.optiontype': {
            'Meta': {'object_name': 'OptionType'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['apparel.OptionType']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'apparel.product': {
            'Meta': {'object_name': 'Product'},
            'category': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['apparel.Category']", 'blank': 'True'}),
            'date_added': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'manufacturer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['apparel.Manufacturer']"}),
            'options': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['apparel.Option']", 'blank': 'True'}),
            'product_image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'product_name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'sku': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'slug': ('django.db.models.fields.SlugField', [], {'db_index': 'True', 'max_length': '80', 'blank': 'True'})
        },
        'apparel.vendor': {
            'Meta': {'object_name': 'Vendor'},
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logotype': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'apparel.vendorproduct': {
            'Meta': {'object_name': 'VendorProduct'},
            'buy_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vendorproduct'", 'to': "orm['apparel.Product']"}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['apparel.Vendor']"})
        },
        'apparel.wardrobe': {
            'Meta': {'object_name': 'Wardrobe'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'products': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['apparel.Product']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }
    
    complete_apps = ['apparel']
