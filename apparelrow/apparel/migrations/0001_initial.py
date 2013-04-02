# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Manufacturer'
        db.create_table(u'apparel_manufacturer', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('logotype', self.gf('django.db.models.fields.files.ImageField')(max_length=127)),
            ('homepage', self.gf('django.db.models.fields.URLField')(max_length=200)),
        ))
        db.send_create_signal(u'apparel', ['Manufacturer'])

        # Adding model 'Brand'
        db.create_table(u'apparel_brand', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('old_name', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('last_update', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'apparel', ['Brand'])

        # Adding model 'OptionType'
        db.create_table(u'apparel_optiontype', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='children', null=True, to=orm['apparel.OptionType'])),
            ('lft', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('rght', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('tree_id', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('level', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
        ))
        db.send_create_signal(u'apparel', ['OptionType'])

        # Adding model 'Option'
        db.create_table(u'apparel_option', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('option_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.OptionType'])),
        ))
        db.send_create_signal(u'apparel', ['Option'])

        # Adding unique constraint on 'Option', fields ['option_type', 'value']
        db.create_unique(u'apparel_option', ['option_type_id', 'value'])

        # Adding model 'Vendor'
        db.create_table(u'apparel_vendor', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('homepage', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('logotype', self.gf('django.db.models.fields.files.ImageField')(max_length=127, null=True, blank=True)),
        ))
        db.send_create_signal(u'apparel', ['Vendor'])

        # Adding model 'Category'
        db.create_table(u'apparel_category', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('name_en', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('name_sv', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('name_da', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('name_no', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('name_order', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('name_order_en', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('name_order_sv', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('name_order_da', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('name_order_no', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('singular_name', self.gf('django.db.models.fields.CharField')(default='', max_length=100)),
            ('singular_name_en', self.gf('django.db.models.fields.CharField')(default='', max_length=100)),
            ('singular_name_sv', self.gf('django.db.models.fields.CharField')(default='', max_length=100)),
            ('singular_name_da', self.gf('django.db.models.fields.CharField')(default='', max_length=100)),
            ('singular_name_no', self.gf('django.db.models.fields.CharField')(default='', max_length=100)),
            ('parent', self.gf('mptt.fields.TreeForeignKey')(blank=True, related_name='children', null=True, to=orm['apparel.Category'])),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
            ('on_front_page', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
            ('lft', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('rght', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('tree_id', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('level', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
        ))
        db.send_create_signal(u'apparel', ['Category'])

        # Adding M2M table for field option_types on 'Category'
        db.create_table(u'apparel_category_option_types', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('category', models.ForeignKey(orm[u'apparel.category'], null=False)),
            ('optiontype', models.ForeignKey(orm[u'apparel.optiontype'], null=False))
        ))
        db.create_unique(u'apparel_category_option_types', ['category_id', 'optiontype_id'])

        # Adding model 'Product'
        db.create_table(u'apparel_product', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('manufacturer', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='products', null=True, on_delete=models.SET_NULL, to=orm['apparel.Brand'])),
            ('static_brand', self.gf('django.db.models.fields.CharField')(default='', max_length=100)),
            ('category', self.gf('mptt.fields.TreeForeignKey')(to=orm['apparel.Category'], null=True, blank=True)),
            ('slug', self.gf('django_extensions.db.fields.AutoSlugField')(allow_duplicates=False, max_length=80, separator=u'-', blank=True, populate_from=('static_brand', 'product_name'), overwrite=False)),
            ('sku', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('product_name', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('date_added', self.gf('django.db.models.fields.DateTimeField')(db_index=True, null=True, blank=True)),
            ('date_published', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('product_image', self.gf('sorl.thumbnail.fields.ImageField')(max_length=255)),
            ('gender', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=1, null=True, blank=True)),
            ('feed_gender', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=1, null=True, blank=True)),
            ('published', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
            ('popularity', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=20, decimal_places=8, db_index=True)),
            ('availability', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'apparel', ['Product'])

        # Adding unique constraint on 'Product', fields ['static_brand', 'sku']
        db.create_unique(u'apparel_product', ['static_brand', 'sku'])

        # Adding M2M table for field options on 'Product'
        db.create_table(u'apparel_product_options', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('product', models.ForeignKey(orm[u'apparel.product'], null=False)),
            ('option', models.ForeignKey(orm[u'apparel.option'], null=False))
        ))
        db.create_unique(u'apparel_product_options', ['product_id', 'option_id'])

        # Adding model 'ProductLike'
        db.create_table(u'apparel_productlike', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('product', self.gf('django.db.models.fields.related.ForeignKey')(related_name='likes', to=orm['apparel.Product'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='product_likes', to=orm['profile.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'apparel', ['ProductLike'])

        # Adding unique constraint on 'ProductLike', fields ['product', 'user']
        db.create_unique(u'apparel_productlike', ['product_id', 'user_id'])

        # Adding model 'ShortProductLink'
        db.create_table(u'apparel_shortproductlink', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('product', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Product'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='short_product_links', to=orm['profile.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal(u'apparel', ['ShortProductLink'])

        # Adding unique constraint on 'ShortProductLink', fields ['product', 'user']
        db.create_unique(u'apparel_shortproductlink', ['product_id', 'user_id'])

        # Adding model 'VendorCategory'
        db.create_table(u'apparel_vendorcategory', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('category', self.gf('mptt.fields.TreeForeignKey')(to=orm['apparel.Category'], null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=555)),
            ('vendor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Vendor'])),
            ('default_gender', self.gf('django.db.models.fields.CharField')(max_length=1, null=True, blank=True)),
            ('override_gender', self.gf('django.db.models.fields.CharField')(max_length=1, null=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
        ))
        db.send_create_signal(u'apparel', ['VendorCategory'])

        # Adding model 'VendorBrand'
        db.create_table(u'apparel_vendorbrand', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('brand', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='vendor_brands', null=True, to=orm['apparel.Brand'])),
            ('vendor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='vendor_brands', to=orm['apparel.Vendor'])),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
        ))
        db.send_create_signal(u'apparel', ['VendorBrand'])

        # Adding model 'VendorProduct'
        db.create_table(u'apparel_vendorproduct', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('product', self.gf('django.db.models.fields.related.ForeignKey')(related_name='vendorproduct', to=orm['apparel.Product'])),
            ('vendor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Vendor'])),
            ('vendor_brand', self.gf('django.db.models.fields.related.ForeignKey')(related_name='vendor_products', null=True, to=orm['apparel.VendorBrand'])),
            ('vendor_category', self.gf('django.db.models.fields.related.ForeignKey')(related_name='vendor_products', null=True, to=orm['apparel.VendorCategory'])),
            ('buy_url', self.gf('django.db.models.fields.URLField')(max_length=555, null=True, blank=True)),
            ('price', self.gf('django.db.models.fields.DecimalField')(db_index=True, null=True, max_digits=10, decimal_places=2, blank=True)),
            ('currency', self.gf('django.db.models.fields.CharField')(max_length=3, null=True, blank=True)),
            ('_original_price', self.gf('django.db.models.fields.DecimalField')(blank=True, null=True, db_column='original_price', decimal_places=2, max_digits=10)),
            ('original_currency', self.gf('django.db.models.fields.CharField')(max_length=3, null=True, blank=True)),
            ('discount_price', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=10, decimal_places=2, blank=True)),
            ('discount_currency', self.gf('django.db.models.fields.CharField')(max_length=3, null=True, blank=True)),
            ('_original_discount_price', self.gf('django.db.models.fields.DecimalField')(blank=True, null=True, db_column='original_discount_price', decimal_places=2, max_digits=10)),
            ('original_discount_currency', self.gf('django.db.models.fields.CharField')(max_length=3, null=True, blank=True)),
            ('availability', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'apparel', ['VendorProduct'])

        # Adding model 'VendorProductVariation'
        db.create_table(u'apparel_vendorproductvariation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('vendor_product', self.gf('django.db.models.fields.related.ForeignKey')(related_name='variations', to=orm['apparel.VendorProduct'])),
            ('in_stock', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'apparel', ['VendorProductVariation'])

        # Adding M2M table for field options on 'VendorProductVariation'
        db.create_table(u'apparel_vendorproductvariation_options', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('vendorproductvariation', models.ForeignKey(orm[u'apparel.vendorproductvariation'], null=False)),
            ('option', models.ForeignKey(orm[u'apparel.option'], null=False))
        ))
        db.create_unique(u'apparel_vendorproductvariation_options', ['vendorproductvariation_id', 'option_id'])

        # Adding model 'Look'
        db.create_table(u'apparel_look', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('slug', self.gf('django_extensions.db.fields.AutoSlugField')(allow_duplicates=False, max_length=80, separator=u'-', blank=True, populate_from=('title',), overwrite=False)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='look', to=orm['profile.User'])),
            ('image', self.gf('sorl.thumbnail.fields.ImageField')(max_length=255, blank=True)),
            ('static_image', self.gf('sorl.thumbnail.fields.ImageField')(max_length=255, null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('tags', self.gf('tagging.fields.TagField')()),
            ('component', self.gf('django.db.models.fields.CharField')(max_length=1, blank=True)),
            ('gender', self.gf('django.db.models.fields.CharField')(default='U', max_length=1)),
            ('popularity', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=20, decimal_places=8, db_index=True)),
            ('width', self.gf('django.db.models.fields.IntegerField')(default=694)),
            ('height', self.gf('django.db.models.fields.IntegerField')(default=524)),
            ('published', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'apparel', ['Look'])

        # Adding model 'LookLike'
        db.create_table(u'apparel_looklike', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('look', self.gf('django.db.models.fields.related.ForeignKey')(related_name='likes', to=orm['apparel.Look'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='look_likes', to=orm['profile.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'apparel', ['LookLike'])

        # Adding unique constraint on 'LookLike', fields ['look', 'user']
        db.create_unique(u'apparel_looklike', ['look_id', 'user_id'])

        # Adding model 'LookComponent'
        db.create_table(u'apparel_lookcomponent', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('look', self.gf('django.db.models.fields.related.ForeignKey')(related_name='components', to=orm['apparel.Look'])),
            ('product', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Product'])),
            ('component_of', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('top', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('left', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('width', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('height', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('z_index', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('rotation', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('positioned', self.gf('django.db.models.fields.CharField')(max_length=1, null=True, blank=True)),
        ))
        db.send_create_signal(u'apparel', ['LookComponent'])

        # Adding model 'TemporaryImage'
        db.create_table(u'apparel_temporaryimage', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=255)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, null=True, blank=True)),
            ('user_id', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal(u'apparel', ['TemporaryImage'])

        # Adding model 'BackgroundImage'
        db.create_table(u'apparel_backgroundimage', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=255, null=True, blank=True)),
        ))
        db.send_create_signal(u'apparel', ['BackgroundImage'])

        # Adding model 'FacebookAction'
        db.create_table(u'apparel_facebookaction', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='facebook_actions', to=orm['profile.User'])),
            ('action', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('action_id', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('object_type', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('object_url', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal(u'apparel', ['FacebookAction'])

        # Adding model 'SynonymFile'
        db.create_table(u'apparel_synonymfile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'apparel', ['SynonymFile'])


    def backwards(self, orm):
        # Removing unique constraint on 'LookLike', fields ['look', 'user']
        db.delete_unique(u'apparel_looklike', ['look_id', 'user_id'])

        # Removing unique constraint on 'ShortProductLink', fields ['product', 'user']
        db.delete_unique(u'apparel_shortproductlink', ['product_id', 'user_id'])

        # Removing unique constraint on 'ProductLike', fields ['product', 'user']
        db.delete_unique(u'apparel_productlike', ['product_id', 'user_id'])

        # Removing unique constraint on 'Product', fields ['static_brand', 'sku']
        db.delete_unique(u'apparel_product', ['static_brand', 'sku'])

        # Removing unique constraint on 'Option', fields ['option_type', 'value']
        db.delete_unique(u'apparel_option', ['option_type_id', 'value'])

        # Deleting model 'Manufacturer'
        db.delete_table(u'apparel_manufacturer')

        # Deleting model 'Brand'
        db.delete_table(u'apparel_brand')

        # Deleting model 'OptionType'
        db.delete_table(u'apparel_optiontype')

        # Deleting model 'Option'
        db.delete_table(u'apparel_option')

        # Deleting model 'Vendor'
        db.delete_table(u'apparel_vendor')

        # Deleting model 'Category'
        db.delete_table(u'apparel_category')

        # Removing M2M table for field option_types on 'Category'
        db.delete_table('apparel_category_option_types')

        # Deleting model 'Product'
        db.delete_table(u'apparel_product')

        # Removing M2M table for field options on 'Product'
        db.delete_table('apparel_product_options')

        # Deleting model 'ProductLike'
        db.delete_table(u'apparel_productlike')

        # Deleting model 'ShortProductLink'
        db.delete_table(u'apparel_shortproductlink')

        # Deleting model 'VendorCategory'
        db.delete_table(u'apparel_vendorcategory')

        # Deleting model 'VendorBrand'
        db.delete_table(u'apparel_vendorbrand')

        # Deleting model 'VendorProduct'
        db.delete_table(u'apparel_vendorproduct')

        # Deleting model 'VendorProductVariation'
        db.delete_table(u'apparel_vendorproductvariation')

        # Removing M2M table for field options on 'VendorProductVariation'
        db.delete_table('apparel_vendorproductvariation_options')

        # Deleting model 'Look'
        db.delete_table(u'apparel_look')

        # Deleting model 'LookLike'
        db.delete_table(u'apparel_looklike')

        # Deleting model 'LookComponent'
        db.delete_table(u'apparel_lookcomponent')

        # Deleting model 'TemporaryImage'
        db.delete_table(u'apparel_temporaryimage')

        # Deleting model 'BackgroundImage'
        db.delete_table(u'apparel_backgroundimage')

        # Deleting model 'FacebookAction'
        db.delete_table(u'apparel_facebookaction')

        # Deleting model 'SynonymFile'
        db.delete_table(u'apparel_synonymfile')


    models = {
        u'apparel.backgroundimage': {
            'Meta': {'object_name': 'BackgroundImage'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
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
            'name_da': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'name_en': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'name_no': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'name_order': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name_order_da': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name_order_en': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name_order_no': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name_order_sv': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name_sv': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'on_front_page': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'option_types': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['apparel.OptionType']", 'symmetrical': 'False', 'blank': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': u"orm['apparel.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'singular_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'singular_name_da': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'singular_name_en': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'singular_name_no': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'singular_name_sv': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        u'apparel.facebookaction': {
            'Meta': {'object_name': 'FacebookAction'},
            'action': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'action_id': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_type': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'object_url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'facebook_actions'", 'to': u"orm['profile.User']"})
        },
        u'apparel.look': {
            'Meta': {'ordering': "['user', 'title']", 'object_name': 'Look'},
            'component': ('django.db.models.fields.CharField', [], {'max_length': '1', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'gender': ('django.db.models.fields.CharField', [], {'default': "'U'", 'max_length': '1'}),
            'height': ('django.db.models.fields.IntegerField', [], {'default': '524'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('sorl.thumbnail.fields.ImageField', [], {'max_length': '255', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'popularity': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '20', 'decimal_places': '8', 'db_index': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django_extensions.db.fields.AutoSlugField', [], {'allow_duplicates': 'False', 'max_length': '80', 'separator': "u'-'", 'blank': 'True', 'populate_from': "('title',)", 'overwrite': 'False'}),
            'static_image': ('sorl.thumbnail.fields.ImageField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'look'", 'to': u"orm['profile.User']"}),
            'width': ('django.db.models.fields.IntegerField', [], {'default': '694'})
        },
        u'apparel.lookcomponent': {
            'Meta': {'object_name': 'LookComponent'},
            'component_of': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'left': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'look': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'components'", 'to': u"orm['apparel.Look']"}),
            'positioned': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['apparel.Product']"}),
            'rotation': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'top': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'z_index': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'apparel.looklike': {
            'Meta': {'unique_together': "(('look', 'user'),)", 'object_name': 'LookLike'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'look': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'likes'", 'to': u"orm['apparel.Look']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'look_likes'", 'to': u"orm['profile.User']"})
        },
        u'apparel.manufacturer': {
            'Meta': {'object_name': 'Manufacturer'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logotype': ('django.db.models.fields.files.ImageField', [], {'max_length': '127'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
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
            'product_image': ('sorl.thumbnail.fields.ImageField', [], {'max_length': '255'}),
            'product_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'sku': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'slug': ('django_extensions.db.fields.AutoSlugField', [], {'allow_duplicates': 'False', 'max_length': '80', 'separator': "u'-'", 'blank': 'True', 'populate_from': "('static_brand', 'product_name')", 'overwrite': 'False'}),
            'static_brand': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'vendors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['apparel.Vendor']", 'through': u"orm['apparel.VendorProduct']", 'symmetrical': 'False'})
        },
        u'apparel.productlike': {
            'Meta': {'unique_together': "(('product', 'user'),)", 'object_name': 'ProductLike'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'likes'", 'to': u"orm['apparel.Product']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'product_likes'", 'to': u"orm['profile.User']"})
        },
        u'apparel.shortproductlink': {
            'Meta': {'unique_together': "(('product', 'user'),)", 'object_name': 'ShortProductLink'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['apparel.Product']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'short_product_links'", 'to': u"orm['profile.User']"})
        },
        u'apparel.synonymfile': {
            'Meta': {'object_name': 'SynonymFile'},
            'content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'apparel.temporaryimage': {
            'Meta': {'object_name': 'TemporaryImage'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '255'}),
            'user_id': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'apparel.vendor': {
            'Meta': {'ordering': "['name']", 'object_name': 'Vendor'},
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logotype': ('django.db.models.fields.files.ImageField', [], {'max_length': '127', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'})
        },
        u'apparel.vendorbrand': {
            'Meta': {'ordering': "['name']", 'object_name': 'VendorBrand'},
            'brand': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'vendor_brands'", 'null': 'True', 'to': u"orm['apparel.Brand']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vendor_brands'", 'to': u"orm['apparel.Vendor']"})
        },
        u'apparel.vendorcategory': {
            'Meta': {'ordering': "['name']", 'object_name': 'VendorCategory'},
            'category': ('mptt.fields.TreeForeignKey', [], {'to': u"orm['apparel.Category']", 'null': 'True', 'blank': 'True'}),
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
        u'apparel.vendorproductvariation': {
            'Meta': {'object_name': 'VendorProductVariation'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_stock': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'options': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['apparel.Option']", 'symmetrical': 'False'}),
            'vendor_product': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'variations'", 'to': u"orm['apparel.VendorProduct']"})
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

    complete_apps = ['apparel']