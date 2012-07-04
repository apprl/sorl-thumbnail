# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.core.exceptions import ObjectDoesNotExist

class Migration(SchemaMigration):

    no_dry_run = True
    
    def forwards(self, orm):
        
        # Adding model 'VendorBrand'
        db.create_table('apparel_vendorbrand', (
            ('brand', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='vendor_brands', null=True, to=orm['apparel.Brand'])),
            ('vendor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='vendor_brands', to=orm['apparel.Vendor'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('apparel', ['VendorBrand'])

        # Adding model 'Brand'
        db.create_table('apparel_brand', (
            ('homepage', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('logotype', self.gf('django.db.models.fields.files.ImageField')(max_length=127, null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
        ))
        db.send_create_signal('apparel', ['Brand'])

        # Copy data from 'Manufacturer' to 'Brand'
        for manufacturer in orm['apparel.Manufacturer'].objects.order_by('id').iterator():
            brand, created = orm['apparel.Brand'].objects.get_or_create(name=manufacturer.name, defaults={'id': manufacturer.id, 'homepage': '', 'logotype': ''})

        # Adding field 'Product.static_brand'
        db.add_column('apparel_product', 'static_brand', self.gf('django.db.models.fields.CharField')(default='', max_length=100), keep_default=False)

        # Changing field 'Product.slug'
        db.alter_column('apparel_product', 'slug', self.gf('django_extensions.db.fields.AutoSlugField')(allow_duplicates=False, max_length=80, separator=u'-', blank=True, populate_from=('static_brand', 'product_name'), overwrite=False))

        # Changing field 'Product.manufacturer'
        db.alter_column('apparel_product', 'manufacturer_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Brand'], null=True, blank=True))

        # Field 'Product.static_brand' should have same value as 'Product.manufacturer.name'
        for product in orm['apparel.Product'].objects.iterator():
            try:
                product.static_brand = product.manufacturer.name
                product.save()
            except ObjectDoesNotExist:
                pass

        # Adding field 'VendorProduct.vendor_brand'
        db.add_column('apparel_vendorproduct', 'vendor_brand', self.gf('django.db.models.fields.related.ForeignKey')(related_name='vendor_products', null=True, to=orm['apparel.VendorBrand']), keep_default=False)

        # Populate 'VendorBrand'
        for vp in orm['apparel.VendorProduct'].objects.iterator():
            try:
                brand = vp.product.manufacturer
                if brand:
                    vendor_brand, created = orm['apparel.VendorBrand'].objects.get_or_create(brand=brand, vendor=vp.vendor, name=brand.name)
                    vp.vendor_brand = vendor_brand
                    vp.save()
            except ObjectDoesNotExist:
                pass

    def backwards(self, orm):
        
        # Deleting model 'VendorBrand'
        db.delete_table('apparel_vendorbrand')

        # Deleting model 'Brand'
        db.delete_table('apparel_brand')

        # Deleting field 'Product.static_brand'
        db.delete_column('apparel_product', 'static_brand')

        # Changing field 'Product.slug'
        db.alter_column('apparel_product', 'slug', self.gf('django_extensions.db.fields.AutoSlugField')(populate_from=('manufacturer', 'product_name'), allow_duplicates=False, max_length=80, separator=u'-', blank=True, overwrite=False))

        # Changing field 'Product.manufacturer'
        db.alter_column('apparel_product', 'manufacturer_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['apparel.Manufacturer']))

        # Deleting field 'VendorProduct.vendor_brand'
        db.delete_column('apparel_vendorproduct', 'vendor_brand_id')
    
    
    models = {
        'apparel.backgroundimage': {
            'Meta': {'object_name': 'BackgroundImage'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'apparel.brand': {
            'Meta': {'object_name': 'Brand'},
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logotype': ('django.db.models.fields.files.ImageField', [], {'max_length': '127', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'apparel.category': {
            'Meta': {'object_name': 'Category'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'name_en': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'name_order': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name_order_en': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name_order_sv': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
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
            'image': ('sorl.thumbnail.fields.ImageField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
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
            'image': ('sorl.thumbnail.fields.ImageField', [], {'max_length': '255', 'blank': 'True'}),
            'is_featured': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'popularity': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '20', 'decimal_places': '8', 'db_index': 'True'}),
            'slug': ('django_extensions.db.fields.AutoSlugField', [], {'allow_duplicates': 'False', 'max_length': '80', 'separator': "u'-'", 'blank': 'True', 'populate_from': "('title',)", 'overwrite': 'False', 'db_index': 'True'}),
            'static_image': ('sorl.thumbnail.fields.ImageField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'look'", 'to': "orm['auth.User']"})
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
            'availability': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'category': ('mptt.fields.TreeForeignKey', [], {'to': "orm['apparel.Category']", 'null': 'True', 'blank': 'True'}),
            'date_added': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'feed_gender': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'gender': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'manufacturer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['apparel.Brand']", 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'options': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['apparel.Option']", 'symmetrical': 'False', 'blank': 'True'}),
            'popularity': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '20', 'decimal_places': '8', 'db_index': 'True'}),
            'product_image': ('sorl.thumbnail.fields.ImageField', [], {'max_length': '255'}),
            'product_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'sku': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'slug': ('django_extensions.db.fields.AutoSlugField', [], {'allow_duplicates': 'False', 'max_length': '80', 'separator': "u'-'", 'blank': 'True', 'populate_from': "('static_brand', 'product_name')", 'overwrite': 'False', 'db_index': 'True'}),
            'static_brand': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
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
        'apparel.vendorbrand': {
            'Meta': {'object_name': 'VendorBrand'},
            'brand': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'vendor_brands'", 'null': 'True', 'to': "orm['apparel.Brand']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vendor_brands'", 'to': "orm['apparel.Vendor']"})
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
            'discount_currency': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True', 'blank': 'True'}),
            'discount_price': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'original_currency': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True', 'blank': 'True'}),
            'original_discount_currency': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True', 'blank': 'True'}),
            'original_discount_price': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'original_price': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'db_index': 'True', 'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vendorproduct'", 'to': "orm['apparel.Product']"}),
            'vendor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['apparel.Vendor']"}),
            'vendor_brand': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vendor_products'", 'null': 'True', 'to': "orm['apparel.VendorBrand']"}),
            'vendor_category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vendor_products'", 'null': 'True', 'to': "orm['apparel.VendorCategory']"})
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
