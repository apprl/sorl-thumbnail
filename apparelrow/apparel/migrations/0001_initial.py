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
            ('logotype', self.gf('django.db.models.fields.files.ImageField')(max_length=127)),
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
            ('logotype', self.gf('django.db.models.fields.files.ImageField')(max_length=127, null=True, blank=True)),
            ('homepage', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
        ))
        db.send_create_signal('apparel', ['Vendor'])

        # Adding model 'Category'
        db.create_table('apparel_category', (
            ('on_front_page', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True, blank=True)),
            ('rght', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('name_sv', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('parent', self.gf('mptt.fields.TreeForeignKey')(blank=True, related_name='children', null=True, to=orm['apparel.Category'])),
            ('name_order_en', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('level', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('lft', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('name_order_sv', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('tree_id', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True, blank=True)),
            ('name_en', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name_order', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
        ))
        db.send_create_signal('apparel', ['Category'])

        # Adding M2M table for field option_types on 'Category'
        db.create_table('apparel_category_option_types', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('category', models.ForeignKey(orm['apparel.category'], null=False)),
            ('optiontype', models.ForeignKey(orm['apparel.optiontype'], null=False))
        ))
        db.create_unique('apparel_category_option_types', ['category_id', 'optiontype_id'])

        # Adding model 'Product'
        db.create_table('apparel_product', (
            ('category', self.gf('mptt.fields.TreeForeignKey')(to=orm['apparel.Category'], null=True, blank=True)),
            ('sku', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('gender', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=1, null=True, blank=True)),
            ('popularity', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('product_name', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('product_image', self.gf('django.db.models.fields.files.ImageField')(max_length=255)),
            ('published', self.gf('django.db.models.fields.BooleanField')(default=True, db_index=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date_added', self.gf('django.db.models.fields.DateTimeField')(db_index=True, null=True, blank=True)),
            ('feed_gender', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=1, null=True, blank=True)),
            ('slug', self.gf('django_extensions.db.fields.AutoSlugField')(allow_duplicates=False, max_length=80, separator=u'-', blank=True, populate_from=('manufacturer', 'product_name'), overwrite=False, db_index=True)),
            ('manufacturer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Manufacturer'])),
        ))
        db.send_create_signal('apparel', ['Product'])

        # Adding M2M table for field options on 'Product'
        db.create_table('apparel_product_options', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('product', models.ForeignKey(orm['apparel.product'], null=False)),
            ('option', models.ForeignKey(orm['apparel.option'], null=False))
        ))
        db.create_unique('apparel_product_options', ['product_id', 'option_id'])

        # Adding model 'ProductLike'
        db.create_table('apparel_productlike', (
            ('product', self.gf('django.db.models.fields.related.ForeignKey')(related_name='likes', to=orm['apparel.Product'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='product_likes', to=orm['auth.User'])),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('apparel', ['ProductLike'])

        # Adding unique constraint on 'ProductLike', fields ['product', 'user']
        db.create_unique('apparel_productlike', ['product_id', 'user_id'])

        # Adding model 'VendorCategory'
        db.create_table('apparel_vendorcategory', (
            ('category', self.gf('mptt.fields.TreeForeignKey')(to=orm['apparel.Category'], null=True, blank=True)),
            ('vendor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Vendor'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=555)),
            ('default_gender', self.gf('django.db.models.fields.CharField')(max_length=1, null=True, blank=True)),
            ('override_gender', self.gf('django.db.models.fields.CharField')(max_length=1, null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('apparel', ['VendorCategory'])

        # Adding model 'VendorProduct'
        db.create_table('apparel_vendorproduct', (
            ('original_price', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=10, decimal_places=2, blank=True)),
            ('product', self.gf('django.db.models.fields.related.ForeignKey')(related_name='vendorproduct', to=orm['apparel.Product'])),
            ('vendor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Vendor'])),
            ('original_currency', self.gf('django.db.models.fields.CharField')(max_length=3, null=True, blank=True)),
            ('vendor_category', self.gf('django.db.models.fields.related.ForeignKey')(related_name='vendorproducts', null=True, to=orm['apparel.VendorCategory'])),
            ('availability', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('currency', self.gf('django.db.models.fields.CharField')(max_length=3, null=True, blank=True)),
            ('buy_url', self.gf('django.db.models.fields.URLField')(max_length=555, null=True, blank=True)),
            ('price', self.gf('django.db.models.fields.DecimalField')(db_index=True, null=True, max_digits=10, decimal_places=2, blank=True)),
        ))
        db.send_create_signal('apparel', ['VendorProduct'])

        # Adding model 'VendorProductVariation'
        db.create_table('apparel_vendorproductvariation', (
            ('vendor_product', self.gf('django.db.models.fields.related.ForeignKey')(related_name='variations', to=orm['apparel.VendorProduct'])),
            ('in_stock', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('apparel', ['VendorProductVariation'])

        # Adding M2M table for field options on 'VendorProductVariation'
        db.create_table('apparel_vendorproductvariation_options', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('vendorproductvariation', models.ForeignKey(orm['apparel.vendorproductvariation'], null=False)),
            ('option', models.ForeignKey(orm['apparel.option'], null=False))
        ))
        db.create_unique('apparel_vendorproductvariation_options', ['vendorproductvariation_id', 'option_id'])

        # Adding model 'Look'
        db.create_table('apparel_look', (
            ('is_featured', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('gender', self.gf('django.db.models.fields.CharField')(default='U', max_length=1)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=255, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('component', self.gf('django.db.models.fields.CharField')(max_length=1, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('slug', self.gf('django_extensions.db.fields.AutoSlugField')(allow_duplicates=False, max_length=80, separator=u'-', blank=True, populate_from=('title',), overwrite=False, db_index=True)),
            ('tags', self.gf('tagging.fields.TagField')()),
        ))
        db.send_create_signal('apparel', ['Look'])

        # Adding model 'LookLike'
        db.create_table('apparel_looklike', (
            ('look', self.gf('django.db.models.fields.related.ForeignKey')(related_name='likes', to=orm['apparel.Look'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='look_likes', to=orm['auth.User'])),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('apparel', ['LookLike'])

        # Adding unique constraint on 'LookLike', fields ['look', 'user']
        db.create_unique('apparel_looklike', ['look_id', 'user_id'])

        # Adding model 'LookComponent'
        db.create_table('apparel_lookcomponent', (
            ('product', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Product'])),
            ('z_index', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('look', self.gf('django.db.models.fields.related.ForeignKey')(related_name='components', to=orm['apparel.Look'])),
            ('top', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('positioned', self.gf('django.db.models.fields.CharField')(max_length=1, null=True, blank=True)),
            ('height', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('width', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('component_of', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('rotation', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('left', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('apparel', ['LookComponent'])

        # Adding unique constraint on 'LookComponent', fields ['product', 'look', 'component_of']
        db.create_unique('apparel_lookcomponent', ['product_id', 'look_id', 'component_of'])

        # Adding model 'Wardrobe'
        db.create_table('apparel_wardrobe', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('apparel', ['Wardrobe'])

        # Adding model 'WardrobeProduct'
        db.create_table('apparel_wardrobe_products', (
            ('wardrobe', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Wardrobe'])),
            ('product', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Product'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('apparel', ['WardrobeProduct'])

        # Adding model 'FirstPageContent'
        db.create_table('apparel_firstpagecontent', (
            ('sorting', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('language', self.gf('django.db.models.fields.CharField')(default='sv', max_length=3)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=127, blank=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=255, null=True, blank=True)),
            ('gender', self.gf('django.db.models.fields.CharField')(default='U', max_length=1)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=255, null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('published', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('pub_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('apparel', ['FirstPageContent'])

        # Adding model 'BackgroundImage'
        db.create_table('apparel_backgroundimage', (
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=255, null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('apparel', ['BackgroundImage'])

        # Adding model 'SynonymFile'
        db.create_table('apparel_synonymfile', (
            ('content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('apparel', ['SynonymFile'])
    
    
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

        # Deleting model 'Product'
        db.delete_table('apparel_product')

        # Removing M2M table for field options on 'Product'
        db.delete_table('apparel_product_options')

        # Deleting model 'ProductLike'
        db.delete_table('apparel_productlike')

        # Removing unique constraint on 'ProductLike', fields ['product', 'user']
        db.delete_unique('apparel_productlike', ['product_id', 'user_id'])

        # Deleting model 'VendorCategory'
        db.delete_table('apparel_vendorcategory')

        # Deleting model 'VendorProduct'
        db.delete_table('apparel_vendorproduct')

        # Deleting model 'VendorProductVariation'
        db.delete_table('apparel_vendorproductvariation')

        # Removing M2M table for field options on 'VendorProductVariation'
        db.delete_table('apparel_vendorproductvariation_options')

        # Deleting model 'Look'
        db.delete_table('apparel_look')

        # Deleting model 'LookLike'
        db.delete_table('apparel_looklike')

        # Removing unique constraint on 'LookLike', fields ['look', 'user']
        db.delete_unique('apparel_looklike', ['look_id', 'user_id'])

        # Deleting model 'LookComponent'
        db.delete_table('apparel_lookcomponent')

        # Removing unique constraint on 'LookComponent', fields ['product', 'look', 'component_of']
        db.delete_unique('apparel_lookcomponent', ['product_id', 'look_id', 'component_of'])

        # Deleting model 'Wardrobe'
        db.delete_table('apparel_wardrobe')

        # Deleting model 'WardrobeProduct'
        db.delete_table('apparel_wardrobe_products')

        # Deleting model 'FirstPageContent'
        db.delete_table('apparel_firstpagecontent')

        # Deleting model 'BackgroundImage'
        db.delete_table('apparel_backgroundimage')

        # Deleting model 'SynonymFile'
        db.delete_table('apparel_synonymfile')
    
    
    models = {
        'apparel.backgroundimage': {
            'Meta': {'object_name': 'BackgroundImage'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'apparel.category': {
            'Meta': {'object_name': 'Category'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'name_en': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'name_order': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name_order_en': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name_order_sv': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name_sv': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'on_front_page': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'option_types': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['apparel.OptionType']", 'symmetrical': 'False', 'blank': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['apparel.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'apparel.firstpagecontent': {
            'Meta': {'object_name': 'FirstPageContent'},
            'content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'gender': ('django.db.models.fields.CharField', [], {'default': "'U'", 'max_length': '1'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "'sv'", 'max_length': '3'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'pub_date': ('django.db.models.fields.DateTimeField', [], {}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'sorting': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'apparel.look': {
            'Meta': {'object_name': 'Look'},
            'component': ('django.db.models.fields.CharField', [], {'max_length': '1', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'gender': ('django.db.models.fields.CharField', [], {'default': "'U'", 'max_length': '1'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '255', 'blank': 'True'}),
            'is_featured': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'slug': ('django_extensions.db.fields.AutoSlugField', [], {'allow_duplicates': 'False', 'max_length': '80', 'separator': "u'-'", 'blank': 'True', 'populate_from': "('title',)", 'overwrite': 'False', 'db_index': 'True'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'apparel.lookcomponent': {
            'Meta': {'unique_together': "(('product', 'look', 'component_of'),)", 'object_name': 'LookComponent'},
            'component_of': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'left': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'look': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'components'", 'to': "orm['apparel.Look']"}),
            'positioned': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['apparel.Product']"}),
            'rotation': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'top': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'z_index': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'apparel.looklike': {
            'Meta': {'unique_together': "(('look', 'user'),)", 'object_name': 'LookLike'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'look': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'likes'", 'to': "orm['apparel.Look']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'look_likes'", 'to': "orm['auth.User']"})
        },
        'apparel.manufacturer': {
            'Meta': {'object_name': 'Manufacturer'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logotype': ('django.db.models.fields.files.ImageField', [], {'max_length': '127'}),
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
            'category': ('mptt.fields.TreeForeignKey', [], {'to': "orm['apparel.Category']", 'null': 'True', 'blank': 'True'}),
            'date_added': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'feed_gender': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'gender': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'manufacturer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['apparel.Manufacturer']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'options': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['apparel.Option']", 'symmetrical': 'False', 'blank': 'True'}),
            'popularity': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'product_image': ('django.db.models.fields.files.ImageField', [], {'max_length': '255'}),
            'product_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'sku': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'slug': ('django_extensions.db.fields.AutoSlugField', [], {'allow_duplicates': 'False', 'max_length': '80', 'separator': "u'-'", 'blank': 'True', 'populate_from': "('manufacturer', 'product_name')", 'overwrite': 'False', 'db_index': 'True'}),
            'vendors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['apparel.Vendor']", 'through': "orm['apparel.VendorProduct']", 'symmetrical': 'False'})
        },
        'apparel.productlike': {
            'Meta': {'unique_together': "(('product', 'user'),)", 'object_name': 'ProductLike'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'likes'", 'to': "orm['apparel.Product']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'product_likes'", 'to': "orm['auth.User']"})
        },
        'apparel.synonymfile': {
            'Meta': {'object_name': 'SynonymFile'},
            'content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'apparel.vendor': {
            'Meta': {'object_name': 'Vendor'},
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logotype': ('django.db.models.fields.files.ImageField', [], {'max_length': '127', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'})
        },
        'apparel.vendorcategory': {
            'Meta': {'object_name': 'VendorCategory'},
            'category': ('mptt.fields.TreeForeignKey', [], {'to': "orm['apparel.Category']", 'null': 'True', 'blank': 'True'}),
            'default_gender': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '555'}),
            'override_gender': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['apparel.Vendor']"})
        },
        'apparel.vendorproduct': {
            'Meta': {'object_name': 'VendorProduct'},
            'availability': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'buy_url': ('django.db.models.fields.URLField', [], {'max_length': '555', 'null': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'original_currency': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True', 'blank': 'True'}),
            'original_price': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'db_index': 'True', 'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vendorproduct'", 'to': "orm['apparel.Product']"}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['apparel.Vendor']"}),
            'vendor_category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vendorproducts'", 'null': 'True', 'to': "orm['apparel.VendorCategory']"})
        },
        'apparel.vendorproductvariation': {
            'Meta': {'object_name': 'VendorProductVariation'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_stock': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'options': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['apparel.Option']", 'symmetrical': 'False'}),
            'vendor_product': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'variations'", 'to': "orm['apparel.VendorProduct']"})
        },
        'apparel.wardrobe': {
            'Meta': {'object_name': 'Wardrobe'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'products': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['apparel.Product']", 'through': "orm['apparel.WardrobeProduct']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'apparel.wardrobeproduct': {
            'Meta': {'object_name': 'WardrobeProduct', 'db_table': "'apparel_wardrobe_products'"},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['apparel.Product']"}),
            'wardrobe': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['apparel.Wardrobe']"})
        },
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
        }
    }
    
    complete_apps = ['apparel']
