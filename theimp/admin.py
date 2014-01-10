import collections
import json
import os.path

from django import forms, utils
from django.conf import settings
from django.contrib import admin
from django.core.files.storage import default_storage
from django.core.urlresolvers import reverse
from django.db.models.loading import get_model
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from sorl.thumbnail import get_thumbnail

from theimp.importer import Importer
from theimp.models import BrandMapping, CategoryMapping
from theimp.parser import Parser


class ProductJSONWidget(forms.Textarea):

    def as_field(self, name, key, value):
        """
        Render key, value as field
        """
        attrs = self.build_attrs(name="%s__%s" % (name, key))
        attrs['value'] = utils.encoding.force_unicode(value)
        return u'<input style="width: 90%%;"%s>' % (forms.util.flatatt(attrs),)

    def as_link_field(self, name, key, value, url):
        return u'<a target="_blank" href="%s">%s</a>' % (url, utils.encoding.force_unicode(value),)

    def as_image_field(self, name, key, value):
        """
        Render key, value as an image field.
        """
        if value:
            images = []
            for image in value:
                image_file = default_storage.open(os.path.join(settings.APPAREL_PRODUCT_IMAGE_ROOT, image.get('path')))
                thumbnail = get_thumbnail(image_file, '100x100')
                images.append(u'<img src="%s">' % (thumbnail.url,))
            return u''.join(images)
        return u''


    def value_from_datadict(self, data, files, name):
        """
        Take values from POST or GET and convert back to JSON..
        Basically what this does is it takes all data variables
        that starts with fieldname__ and converts
        fieldname__key__key = value into json[key][key] = value
        TODO: cleaner syntax?
        TODO: integer values don't need to be stored as string
        """
        json_obj = {}

        separator = "__"

        for key, value in data.items():
            if key.startswith(name+separator):
                dict_key = key[len(name+separator):].split(separator)

                prev_dict = json_obj
                for k in dict_key[:-1]:
                    if prev_dict.has_key(k):
                        prev_dict = prev_dict[k]
                    else:
                        prev_dict[k] = {}
                        prev_dict = prev_dict[k]

                if value is not None:
                    prev_dict[dict_key[-1:][0]] = value

        return json.dumps(prev_dict)

    def render(self, name, value, attrs=None):
        if value is None or value == '':
            value = '{}'

        json_obj = json.loads(value)
        hide_keys = ['key', 'images', 'image_urls', 'affiliate', 'vendor', 'vendor_id', 'brand', 'category', 'url']
        remove_keys = ['image_urls', 'vendor_id']
        keys = sorted(json_obj.get('scraped', {}).keys())
        table = collections.OrderedDict()
        for key in keys:
            if key in remove_keys:
                continue

            table[key] = {}
            for layer in ['scraped', 'parsed', 'manual', 'final']:
                key_value = json_obj.get(layer, {}).get(key, '')
                if key == 'colors' and layer == 'manual':
                    table[key][layer] = 'TODO'
                elif layer == 'manual' and key not in hide_keys:
                    table[key][layer] = self.as_field(name, 'manual__%s' % (key,), key_value)
                elif key == 'images':
                    table[key][layer] = self.as_image_field(name, 'manual__%s' % (key,), key_value)
                elif key == 'brand' and layer == 'scraped':
                    try:
                        brand = BrandMapping.objects.get(brand=key_value, vendor__name=json_obj.get(layer, {}).get('vendor', ''))
                        url = reverse('admin:theimp_brandmapping_change', args=[brand.pk])
                        table[key][layer] = self.as_link_field(name, key, key_value, url)
                    except BrandMapping.DoesNotExist:
                        table[key][layer] = 'MISSING BRAND: %s' % (key_value,)
                elif key == 'category' and layer == 'scraped':
                    try:
                        category = CategoryMapping.objects.get(category=key_value, vendor__name=json_obj.get(layer, {}).get('vendor', ''))
                        url = reverse('admin:theimp_categorymapping_change', args=[category.pk])
                        table[key][layer] = self.as_link_field(name, key, key_value, url)
                    except CategoryMapping.DoesNotExist:
                        table[key][layer] = 'MISSING CATEGORY: %s' % (key_value,)
                else:
                    table[key][layer] = key_value

        rendered = render_to_string('json_widget.html', {'table': table, 'raw': value})

        return utils.safestring.mark_safe(rendered)


class ProductAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ProductAdminForm, self).__init__(*args, **kwargs)
        self.fields['json'].widget = ProductJSONWidget()

    def clean_json(self):
        json_obj = json.loads(self.instance.json)
        json_obj['manual'] = json.loads(self.cleaned_data['json'])

        return json.dumps(json_obj)

    class Meta:
        model = get_model('theimp', 'Product')


class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    ordering = ('-modified',)
    list_display = ('key', 'vendor', 'is_validated', 'is_dropped', 'modified', 'parsed_date', 'imported_date')
    list_filter = ('is_validated', 'is_dropped', 'vendor')
    readonly_fields = ('key', 'is_validated', 'created', 'modified', 'vendor', 'parsed_date', 'imported_date')
    search_fields = ('key',)
    actions = ('parse_products',)
    save_on_top = True

    def save_model(self, request, obj, form, change):
        parser = Parser()
        parser.parse(obj)
        obj.save()

    def parse_products(self, request, queryset):
        parser = Parser()
        for product in queryset.iterator():
            parser.parse(product)


class VendorAdmin(admin.ModelAdmin):
    exclude = ('is_active',)
    list_display = ('name', 'affiliate_identifier', 'comment', 'created', 'modified')
    list_filter = ('is_active',)
    readonly_fields = ('name', 'created', 'modified')


class IsMappedBrandListFilter(admin.SimpleListFilter):
    title = _('is mapped')
    parameter_name = 'is_mapped'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('yes')),
            ('no', _('no')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(mapped_brand__isnull=False)
        if self.value() == 'no':
            return queryset.filter(mapped_brand__isnull=True)


class BrandMappingAdmin(admin.ModelAdmin):
    list_display = ('brand', 'vendor', 'mapped_brand')
    list_filter = (IsMappedBrandListFilter, 'vendor')
    readonly_fields = ('vendor', 'brand', 'created', 'modified')
    search_fields = ('brand',)

class IsMappedCategoryListFilter(admin.SimpleListFilter):
    title = _('is mapped')
    parameter_name = 'is_mapped'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('yes')),
            ('no', _('no')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(mapped_category__isnull=False)
        if self.value() == 'no':
            return queryset.filter(mapped_category__isnull=True)


class CategoryMappingAdmin(admin.ModelAdmin):
    list_display = ('category', 'vendor', 'mapped_category', 'category_ancestors')
    list_filter = (IsMappedCategoryListFilter, 'vendor')
    readonly_fields = ('vendor', 'category', 'created', 'modified')
    search_fields = ('category',)
    list_editable = ('mapped_category',)

    def category_ancestors(self, category):
        result = []
        if category.mapped_category:
            result = [c.name for c in category.mapped_category.get_ancestors()]

        return ' > '.join(result)


class MappingAdmin(admin.ModelAdmin):
    list_display = ('mapping_key', 'mapping_type', 'mapping_aliases')
    readonly_fields = ('mapping_key', 'mapping_type')


admin.site.register(get_model('theimp', 'Product'), ProductAdmin)
admin.site.register(get_model('theimp', 'Vendor'), VendorAdmin)
admin.site.register(get_model('theimp', 'BrandMapping'), BrandMappingAdmin)
admin.site.register(get_model('theimp', 'CategoryMapping'), CategoryMappingAdmin)
admin.site.register(get_model('theimp', 'Mapping'), MappingAdmin)
