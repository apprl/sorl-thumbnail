from django.http import HttpResponseRedirect
from django.contrib import admin
from django.db.models import Count
from django.forms import Form, CharField, MultipleHiddenInput, ModelChoiceField, ModelMultipleChoiceField
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.db.models.loading import get_model
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse

from apparelrow.apparel.models import *
from modeltranslation.admin import TranslationAdmin
from sorl.thumbnail import get_thumbnail
from mptt.forms import TreeNodeChoiceField
from mptt.admin import MPTTModelAdmin

#
# PRODUCT
#

class ProductAdmin(admin.ModelAdmin):
    list_display = ('image', 'product_name', 'category', 'gender', 'manufacturer', 'sku', 'published',)
    list_filter = ['category', 'gender', 'vendors', 'published']
    list_editable = ['category', 'gender', 'published']
    list_display_links = ['product_name']
    actions = ['publish', 'hide', 'change_category', 'change_options']
    search_fields = ['product_name']
    list_per_page = 25
    raw_id_fields = ('manufacturer',)

    def image(self, obj):
        try:
            thumbnail = get_thumbnail(obj.product_image, '112x145', crop=False, format='PNG', transparent=True)
            return u'<a href="%s"><img style="width: 50px; height: 50px;" src="%s" /></a>' % (obj.product_image.url, thumbnail.url,)
        except IOError:
            return u'<a href="%s">no image</a>' % (obj.product_image.url,)

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
                return ['published', 'static_brand']
        return ['static_brand']

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
# SHORT STORE LINK
#

class ShortStoreLinkAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'template', 'link')

    def link(self, instance):
        current_site = Site.objects.get_current()

        return 'http://{}{}'.format(current_site.domain, reverse('store-short-link', args=[instance.link()]))


admin.site.register(ShortStoreLink, ShortStoreLinkAdmin)


#
# SHORT PRODUCT LINK
#

class ShortProductLinkAdmin(admin.ModelAdmin):
    raw_id_fields = ('product', 'user')
    list_display = ('product', 'user', 'created')


admin.site.register(ShortProductLink, ShortProductLinkAdmin)


#
# SHORT DOMAIN LINK
#

class ShortDomainLinkAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('url', 'user', 'vendor', 'created')

admin.site.register(ShortDomainLink, ShortDomainLinkAdmin)


#
# DOMAIN DEEP LINKING
#

class DomainDeepLinkingAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'domain', 'template')

admin.site.register(DomainDeepLinking, DomainDeepLinkingAdmin)


#
# LOOK
#

def rebuild_static_image(modeladmin, request, queryset):
    for look in queryset:
        get_model('apparel', 'Look').build_static_image(look.pk)
rebuild_static_image.short_description = 'Rebuild static images for marked looks'

def recalculate_gender(modeladmin, request, queryset):
    for look in queryset:
        get_model('apparel', 'Look').calculate_gender(look.pk)
recalculate_gender.short_description = 'Recalculate gender for marked looks'

class LookComponentInline(admin.TabularInline):
    model = LookComponent
    extra = 0
    readonly_fields = ('product', 'component_of', 'top', 'left', 'width', 'height', 'z_index', 'rotation', 'positioned', 'flipped')
    raw_id_fields = ('product',)

    def has_delete_permission(self, request, obj=None):
        return False

class LookAdmin(admin.ModelAdmin):
    ordering = ('-created',)
    readonly_fields = ('width', 'height', 'image_width', 'image_height', 'created', 'modified')
    list_display = ('title', 'user', 'component', 'gender', 'created', 'has_static_look_image')
    list_filter = ('gender', 'component')
    raw_id_fields = ('user',)
    actions = [rebuild_static_image, recalculate_gender]
    inlines = [LookComponentInline]

    def has_static_look_image(self, obj):
        return True if obj.static_image else False

admin.site.register(Look, LookAdmin)

#
# LOOK EMBED
#

class LookEmbedAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'look', 'user', 'language', 'width', 'created')
    list_filter = ('language',)

admin.site.register(LookEmbed, LookEmbedAdmin)


#
# LOOK COMPONENT
#

class LookComponentAdmin(admin.ModelAdmin):
    raw_id_fields = ('product',)

admin.site.register(LookComponent, LookComponentAdmin)

class ShopProductInline(admin.TabularInline):
    model = ShopProduct

#
# SHOP
#

class ShopAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created')
    inlines = [
        ShopProductInline,
    ]

admin.site.register(Shop, ShopAdmin)

#
# SHOP EMBED
#

class ShopEmbedAdmin(admin.ModelAdmin):
    list_display = ('user', )

admin.site.register(ShopEmbed, ShopEmbedAdmin)


#
# BRAND
#

class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'id', 'followers_count')
    readonly_fields = ('old_name',)
    search_fields = ('name',)

    def followers_count(self, brand):
        if brand.user and brand.user.followers_count:
            return brand.user.followers_count

        return 0

admin.site.register(Brand, BrandAdmin)

#
# CATEGORY
#

class CategoryAdmin(TranslationAdmin, MPTTModelAdmin):
    list_display = ('name', 'ancestors', 'on_front_page')
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

    # XXX: disabled, too slow with MySQL
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
        result = []
        if vendor_category.category:
            result = [c.name for c in vendor_category.category.get_ancestors()]

        return ' > '.join(result)

    def queryset(self, request):
        qs = super(VendorCategoryAdmin, self).queryset(request)
        return qs.annotate(models.Count('vendor_products'))

    def num_products(self, vendor_category):
        return vendor_category.vendor_products.count()
    num_products.admin_order_field = 'vendor_products__count'

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
# VENDOR BRAND
#


class BrandIsNullListFilter(admin.SimpleListFilter):
    title = _('brand mapped')
    parameter_name = 'brand_mapped'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('Yes')),
            ('no', _('No')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(brand__isnull=False)
        elif self.value() == 'no':
            return queryset.filter(brand__isnull=True)

class VendorBrandAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'name', 'brand', 'num_products')
    list_filter = ('vendor', BrandIsNullListFilter)
    list_display_links = ('name',)
    list_per_page = 25
    raw_id_fields = ('brand',)
    search_fields = ('name',)
    readonly_fields = ('vendor', 'name')

    def queryset(self, request):
        qs = super(VendorBrandAdmin, self).queryset(request)
        return qs.annotate(models.Count('vendor_products'))

    def num_products(self, vendor_brand):
        return vendor_brand.vendor_products.count()
    num_products.admin_order_field = 'vendor_products__count'

admin.site.register(VendorBrand, VendorBrandAdmin)

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

class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider')
    raw_id_fields = ['user']

admin.site.register(Vendor, VendorAdmin)

#
# VENDOR PRODUCT
#

class VendorProductVariationInline(admin.StackedInline):
    model = VendorProductVariation
    extra = 0

class VendorProductAdmin(admin.ModelAdmin):
    raw_id_fields = ['product', 'vendor_category', 'vendor_brand']
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


class InternalReferralAdmin(admin.ModelAdmin):
    list_display = ('cookie_id', 'old_cookie_id', 'user_id', 'sid', 'page', 'created', 'expires', 'expired')
    list_filter = ('expired',)
    search_fields = ('cookie_id',)

admin.site.register(InternalReferral, InternalReferralAdmin)


#
# User data
#

class LookLikeAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified')
    fields = ('look', 'user', 'active', 'created', 'modified')
    raw_id_fields = ['look', 'user']
    list_display = ('look', 'user', 'created', 'modified', 'active')
    list_filter = ('active',)

admin.site.register(LookLike, LookLikeAdmin)

class ProductLikeAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified')
    fields = ('product', 'user', 'active', 'created', 'modified')
    raw_id_fields = ['product', 'user']
    list_display = ('product', 'user', 'created', 'modified', 'active')
    list_filter = ('active',)

admin.site.register(ProductLike, ProductLikeAdmin)

# Search synonyms

admin.site.register(SynonymFile)

admin.site.register(BackgroundImage)
