from django.http import HttpResponseRedirect
from django.contrib import admin
from django.db.models import Count
from django.forms import Form, CharField, MultipleHiddenInput, ModelChoiceField, ModelMultipleChoiceField
from django.shortcuts import render_to_response
from django.template import RequestContext

from apparel.models import *
from modeltranslation.admin import TranslationAdmin
from sorl.thumbnail.main import DjangoThumbnail
from mptt.forms import TreeNodeChoiceField
from mptt.admin import MPTTModelAdmin

#
# Products
#

class ProductAdmin(admin.ModelAdmin):
    list_display = ('image', 'product_name', 'category', 'gender', 'manufacturer', 'sku', 'published',)
    list_filter = ['category', 'gender', 'manufacturer', 'vendors', 'published']
    list_editable = ['category', 'gender', 'published']
    list_display_links = ['product_name']
    actions = ['publish', 'hide', 'change_category', 'change_options']

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

class LookAdmin(admin.ModelAdmin):
    raw_id_fields = ('products',)
    list_display = ('title', 'user', 'component', 'is_featured')
    list_filter = ['is_featured']

admin.site.register(Look, LookAdmin)

class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name', 'active',)
    list_filter = ['active']

admin.site.register(Manufacturer, ManufacturerAdmin)

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
        result = Product.objects.values('category').filter(category=category).annotate(Count('category')).get()
        if result and 'category__count' in result:
            return result['category__count']

admin.site.register(Category, CategoryAdmin)

class VendorCategoryAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'name', 'default_gender', 'category', 'category_ancestors', 'num_products',)
    list_filter = ['vendor', 'category', 'default_gender']
    list_editable = ['default_gender', 'category']
    list_display_links = ['name']

    def category_ancestors(self, vendor_category):
        return ' > '.join([c.name for c in vendor_category.category.get_ancestors()])

    def num_products(self, vendor_category):
        result = VendorProduct.objects.values('vendor_category').filter(vendor_category=vendor_category).annotate(Count('vendor_category')).get()
        if result and 'vendor_category__count' in result:
            return result['vendor_category__count']

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

# Search synonyms

admin.site.register(SynonymFile)

admin.site.register(FirstPageContent, FirstPageContentAdmin)

