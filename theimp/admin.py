import collections
import json
import os.path

from django import forms, utils
from django.conf import settings
from django.contrib import admin
from django.core.files.storage import default_storage
from django.db.models.loading import get_model
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from hotqueue import HotQueue

from sorl.thumbnail import get_thumbnail

from theimp.parser import Parser
from theimp.importer import Importer


class ProductJSONWidget(forms.Textarea):

    def as_field(self, name, key, value):
        """
        Render key, value as field
        """
        attrs = self.build_attrs(name="%s__%s" % (name, key))
        attrs['value'] = utils.encoding.force_unicode(value)
        return u'<input style="width: 90%%;"%s>' % (forms.util.flatatt(attrs),)

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
                if layer == 'manual' and key not in hide_keys:
                    table[key][layer] = self.as_field(name, 'manual__%s' % (key,), json_obj.get(layer, {}).get(key, ''))
                elif key == 'images':
                    table[key][layer] = self.as_image_field(name, 'manual__%s' % (key,), json_obj.get(layer, {}).get(key, ''))
                else:
                    table[key][layer] = json_obj.get(layer, {}).get(key, '')

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
    list_display = ('key', 'vendor', 'is_auto_validated', 'created', 'modified')
    list_filter = ('is_auto_validated', 'is_manual_validated', 'dropped', 'vendor')
    readonly_fields = ('key', 'is_auto_validated', 'created', 'modified', 'vendor', 'dropped')
    search_fields = ('key',)
    actions = ('add_to_parse_queue',)
    save_on_top = True

    #def save_model(self, request, obj, form, change):
        #parser = Parser()
        #importer = Importer()

        #is_valid = parser.parse(obj)
        #importer.site_import(obj, is_valid)

        #obj.save()

    def add_to_parse_queue(self, request, queryset):
        parse_queue = HotQueue(settings.THEIMP_QUEUE_PARSE,
                               host=settings.THEIMP_REDIS_HOST,
                               port=settings.THEIMP_REDIS_PORT,
                               db=settings.THEIMP_REDIS_DB)

        for product_id in queryset.values_list('pk', flat=True):
            parse_queue.put(product_id)


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
    list_display = ('category', 'vendor', 'mapped_category')
    list_filter = (IsMappedCategoryListFilter, 'vendor')
    readonly_fields = ('vendor', 'category', 'created', 'modified')
    search_fields = ('category',)


class MappingAdmin(admin.ModelAdmin):
    list_display = ('mapping_key', 'mapping_type', 'mapping_aliases')
    readonly_fields = ('mapping_key', 'mapping_type')


class BrandAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified')


class CategoryAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified')


admin.site.register(get_model('theimp', 'Product'), ProductAdmin)
admin.site.register(get_model('theimp', 'Vendor'), VendorAdmin)
admin.site.register(get_model('theimp', 'BrandMapping'), BrandMappingAdmin)
admin.site.register(get_model('theimp', 'CategoryMapping'), CategoryMappingAdmin)
admin.site.register(get_model('theimp', 'Mapping'), MappingAdmin)
admin.site.register(get_model('theimp', 'Brand'), BrandAdmin)
admin.site.register(get_model('theimp', 'Category'), CategoryAdmin)
