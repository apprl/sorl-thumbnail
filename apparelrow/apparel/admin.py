from django.http import HttpResponseRedirect
from django.contrib import admin
from django.db.models import Count
from django.forms import Form, CharField, MultipleHiddenInput, ModelChoiceField, ModelMultipleChoiceField
from django.shortcuts import render_to_response
from django.template import RequestContext

from apparel.models import *
from modeltranslation.admin import TranslationAdmin
from sorl.thumbnail import get_thumbnail
from mptt.forms import TreeNodeChoiceField
from mptt.admin import MPTTModelAdmin

#
# PRODUCT
#

class ProductAdmin(admin.ModelAdmin):
    list_display = ('image', 'product_name', 'category', 'gender', 'manufacturer', 'sku', 'published',)
    list_filter = ['category', 'gender', 'manufacturer', 'vendors', 'published']
    list_editable = ['category', 'gender', 'published']
    list_display_links = ['product_name']
    actions = ['publish', 'hide', 'change_category', 'change_options']
    list_per_page = 50

    def image(self, obj):
        thumbnail = get_thumbnail(obj.product_image, '50x50', crop='noop', quality=99)
        return u'<a href="%s"><img src="%s" /></a>' % (obj.product_image.url, thumbnail.url,)

    image.short_description = 'Image'
    image.allow_tags = True

    def publish(self, request, queryset):
        queryset.update(published=True)
    publish.short_description = "Publish selected products"
    
    def hide(self, request, queryset):
        queryset.update(published=False)
    hide.short_description = "Hide selected products"

    def get_readonly_fields(self, request, obj=None):
        if obj:
            if ProductLike.objects.filter(active=True, product=obj) or LookComponent.objects.filter(product=obj):
                return ['published']
        return []

    class ChangeCategoryForm(Form):
        _selected_action = CharField(widget=MultipleHiddenInput)
        category = TreeNodeChoiceField(queryset=Category.objects.all())

    def change_category(self, request, queryset):
        form = None
        if 'apply' in request.POST:
            form = self.ChangeCategoryForm(request.POST)
            if form.is_valid():
                category = form.cleaned_data['category']
                count = 0
                for product in queryset:
                    product.category = category
                    product.save()
                    count += 1
                plural = 's' if count != 1 else ''
                self.message_user(request, "Successfully changed category to %s for %d product%s." % (category, count, plural))
                return HttpResponseRedirect(request.get_full_path())

        if not form:
            form = self.ChangeCategoryForm(initial={'_selected_action': request.POST.getlist(admin.ACTION_CHECKBOX_NAME)})

        return render_to_response('admin/change_category.html', 
                {'products': queryset, 'category_form': form}, context_instance=RequestContext(request))

    change_category.short_description = "Change category for selected products"

    class ChangeOptionsForm(Form):
        _selected_action = CharField(widget=MultipleHiddenInput)
        options = ModelMultipleChoiceField(queryset=Option.objects.all())

    def change_options(self, request, queryset):
        form = None
        if 'change' in request.POST:
            form = self.ChangeOptionsForm(request.POST)
            if form.is_valid():
                count = 0
                for product in queryset:
                    product.options = form.cleaned_data['options']
                    product.save()
                    count += 1
                plural = 's' if count != 1 else ''
                self.message_user(request, "Successfully changed options for %d product%s." % (count, plural))
                return HttpResponseRedirect(request.get_full_path())

        if not form:
            form = self.ChangeOptionsForm(initial={'_selected_action': request.POST.getlist(admin.ACTION_CHECKBOX_NAME)})

        return render_to_response('admin/change_options.html', 
                {'products': queryset, 'options_form': form}, context_instance=RequestContext(request))

    change_options.short_description = "Change options for selected products"

admin.site.register(Product, ProductAdmin)

#
# LOOK
#

class LookAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'component', 'is_featured', 'gender')
    list_filter = ['is_featured', 'gender']

admin.site.register(Look, LookAdmin)

#
# LOOK COMPONENT
#

class LookComponentAdmin(admin.ModelAdmin):
    raw_id_fields = ('product',)

admin.site.register(LookComponent, LookComponentAdmin)

#
# MANUFACTURER
#

class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name', 'active',)
    list_filter = ['active']

admin.site.register(Manufacturer, ManufacturerAdmin)

#
# CATEGORY
#

class CategoryAdmin(TranslationAdmin, MPTTModelAdmin):
    list_display = ('name', 'ancestors', 'on_front_page', 'num_products')
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

    def num_products(self, category):
        p = Product.objects.filter(category=category).count()

        available_p = 0
        if p > 0:
            available_p = Product.valid_objects.filter(category=category).count()

        return '%s (%s)' % (p, available_p)

admin.site.register(Category, CategoryAdmin)

#
# VENDOR CATEGORY
#

class VendorCategoryAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'name', 'override_gender', 'default_gender', 'category', 'category_ancestors', 'num_products',)
    list_filter = ['vendor', 'category', 'override_gender', 'default_gender']
    list_editable = ['override_gender', 'default_gender', 'category']
    list_display_links = ['name']
    actions = ['reset_gender']
    list_per_page = 50

    def category_ancestors(self, vendor_category):
        return ' > '.join([c.name for c in vendor_category.category.get_ancestors()])

    def num_products(self, vendor_category):
        vp = VendorProduct.objects.filter(vendor_category=vendor_category).count()

        available_vp = 0
        if vp > 0:
            available_vp = VendorProduct.objects.filter(vendor_category=vendor_category).exclude(availability=0).count()

        return '%s (%s)' % (vp, available_vp)

    def reset_gender(self, request, queryset):
        num_products = 0
        num_vendor_categories = 0
        for vendor_category in queryset:
            num_vendor_categories += 1
            vendor_category.override_gender = ''
            for product in Product.objects.filter(vendorproduct__vendor_category=vendor_category):
                num_products += 1
                product.gender = product.feed_gender
                if product.gender is None and vendor_category.default_gender is not None:
                    product.gender = vendor_category.default_gender
                product.save()
            vendor_category.save()

        self.message_user(request, "Successfully reseted %s products in %s vendor categories" % (num_products, num_vendor_categories))

    reset_gender.short_description = "Reset gender for all products related to this vendor category"

admin.site.register(VendorCategory, VendorCategoryAdmin)

#
# OPTION TYPE
#

class OptionTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']
    list_filter = ['parent']

admin.site.register(OptionType, OptionTypeAdmin)

#
# OPTION
#

class OptionAdmin(admin.ModelAdmin):
    list_display = ['value', 'option_type']
    list_filter = ['option_type']

admin.site.register(Option, OptionAdmin)

#
# VENDOR
#

admin.site.register(Vendor)

#
# VENDOR PRODUCT
#

class VendorProductVariationInline(admin.StackedInline):
    model = VendorProductVariation
    extra = 0

class VendorProductAdmin(admin.ModelAdmin):
    raw_id_fields = ['product', 'vendor_category']
    list_display = ['product', 'vendor', 'price', 'in_stock']
    list_filter = ['vendor']
    inlines = [VendorProductVariationInline]
    list_per_page = 50

    def in_stock(self, vp):
        if vp.availability is None:
            return 'No information available'
        elif vp.availability == 0:
            return 'Out of stock'
        elif vp.availability < 0:
            return 'In stock'
        else:
            return '%i %s' % (vp.availability, 'items in stock')


admin.site.register(VendorProduct, VendorProductAdmin)


#
# User data
#

class LookLikeAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified')
    fields = ('look', 'user', 'active', 'created', 'modified')
    raw_id_fields = ['look', 'user']
    list_display = ('look', 'user', 'created', 'modified', 'active')
    list_filter = ('active', 'user')

admin.site.register(LookLike, LookLikeAdmin)

class ProductLikeAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified')
    fields = ('product', 'user', 'active', 'created', 'modified')
    raw_id_fields = ['product', 'user']
    list_display = ('product', 'user', 'created', 'modified', 'active')
    list_filter = ('active', 'user')

admin.site.register(ProductLike, ProductLikeAdmin)

# Front Page

class FirstPageContentAdmin(admin.ModelAdmin):
    list_display = ['title', 'pub_date', 'published']
    list_filter = ['published', 'language', 'gender']

admin.site.register(FirstPageContent, FirstPageContentAdmin)

# Search synonyms

admin.site.register(SynonymFile)

admin.site.register(BackgroundImage)
