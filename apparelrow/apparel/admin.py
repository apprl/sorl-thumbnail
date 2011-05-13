from apparel.models import *
from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from sorl.thumbnail.main import DjangoThumbnail


#
# Products
#

class ProductAdmin(admin.ModelAdmin):
    list_display = ('image', 'product_name', 'category', 'gender', 'manufacturer', 'sku', 'published',)
    list_filter = ['category', 'gender', 'manufacturer', 'vendors', 'published']
    list_editable = ['category', 'gender', 'published']
    list_display_links = ['product_name']
    actions = ['publish', 'hide']

    def image(self, obj):
        thumbnail = DjangoThumbnail(obj.product_image, (50, 50))
        return u'<a href="%s"><img src="%s" /></a>' % (obj.product_image.url, thumbnail.absolute_url,)
    image.short_description = 'Image'
    image.allow_tags = True

    def publish(self, request, queryset):
        queryset.update(published=True)
    publish.short_description = "Publish selected products"
    
    def hide(self, request, queryset):
        queryset.update(published=False)
    hide.short_description = "Hide selected products"

admin.site.register(Product, ProductAdmin)

class LookAdmin(admin.ModelAdmin):
    raw_id_fields = ('products',)
    list_display = ('title', 'user', 'component', 'is_featured')
    list_filter = ['is_featured']

admin.site.register(Look, LookAdmin)

class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name', 'active',)
    list_filter = ['active']

admin.site.register(Manufacturer, ManufacturerAdmin)

class CategoryAdmin(TranslationAdmin):
    list_display = ('name', 'ancestors', 'on_front_page',)
    list_filter = ['parent', 'on_front_page']
    actions = ['publish_on_front_page', 'hide_on_front_page']

    def publish_on_front_page(self, request, queryset):
        queryset.update(on_front_page=True)
    publish_on_front_page.short_description = "Publish selected on front page"
    
    def hide_on_front_page(self, request, queryset):
        queryset.update(on_front_page=False)
    hide_on_front_page.short_description = "Hide selected on front page"
    
    def ancestors(self, category):
        return ' > '.join([c.name for c in category.get_ancestors()])

admin.site.register(Category, CategoryAdmin)

class VendorCategoryAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'name', 'default_gender', 'category',)
    list_filter = ['vendor', 'category', 'default_gender']
    list_editable = ['default_gender', 'category']
    list_display_links = ['name']

admin.site.register(VendorCategory, VendorCategoryAdmin)

class OptionTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']
    list_filter = ['parent']

admin.site.register(OptionType, OptionTypeAdmin)

class OptionAdmin(admin.ModelAdmin):
    list_display = ['value', 'option_type']
    list_filter = ['option_type']

admin.site.register(Option, OptionAdmin)

admin.site.register(Vendor)

class VendorProductVariationInline(admin.StackedInline):
    model = VendorProductVariation
    extra = 0

class VendorProductAdmin(admin.ModelAdmin):
    raw_id_fields = ['product', 'vendor_category']
    list_display = ['product', 'vendor', 'price']
    list_filter = ['vendor']
    inlines = [VendorProductVariationInline]

admin.site.register(VendorProduct, VendorProductAdmin)


#
# User data
#

admin.site.register(LookComponent)
admin.site.register(Wardrobe)

# Front Page

class FirstPageContentAdmin(admin.ModelAdmin):
    list_display = ['title', 'pub_date', 'published']
    list_filter = ['published']

admin.site.register(FirstPageContent, FirstPageContentAdmin)

