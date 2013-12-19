import collections
import json

from django import forms, utils
from django.contrib import admin
from django.db.models.loading import get_model
from django.template.loader import render_to_string


class ProductJSONWidget(forms.Textarea):

    def as_field(self, name, key, value):
        """
        Render key, value as field
        """
        attrs = self.build_attrs(name="%s__%s" % (name, key))
        attrs['value'] = utils.encoding.force_unicode(value)
        return u'<input style="width: 90%%;"%s>' % (forms.util.flatatt(attrs),)

    def to_fields(self, name, json_obj):
        """
        Get list of rendered fields for json object
        """
        inputs = []
        for key, value in json_obj.items():
            if type(value) in (str, unicode, int):
                inputs.append((key, self.as_field(name, key, value)))
            elif type(value) in (dict,):
                inputs.extend(self.to_fields("%s__%s" % (name, key), value))

        return inputs

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

                if value:
                    prev_dict[dict_key[-1:][0]] = value

        return json.dumps(prev_dict)

    def render(self, name, value, attrs=None):
        if value is None or value == '':
            value = '{}'

        json_obj = json.loads(value)
        inputs = self.to_fields(name, json_obj.get('manual', {}))

        remove_keys = ['key', 'images', 'image_urls', 'affiliate', 'vendor', 'vendor_id']
        keys = sorted(json_obj.get('scraped', {}).keys())
        table = collections.OrderedDict()
        for key in keys:
            table[key] = {}
            for layer in ['scraped', 'parsed', 'manual', 'final']:
                if layer == 'manual' and key not in remove_keys:
                    table[key][layer] = self.as_field(name, 'manual__%s' % (key,), json_obj.get(layer, {}).get(key, ''))
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


class VendorAdmin(admin.ModelAdmin):
    exclude = ('is_active',)
    list_display = ('name', 'affiliate_identifier', 'comment', 'created', 'modified')
    list_filter = ('is_active',)
    readonly_fields = ('name', 'created', 'modified')


class BrandMappingAdmin(admin.ModelAdmin):
    list_display = ('brand', 'vendor', 'mapped_brand')
    list_filter = ('vendor',)
    readonly_fields = ('vendor', 'brand', 'created', 'modified')


class CategoryMappingAdmin(admin.ModelAdmin):
    list_display = ('category', 'vendor', 'mapped_category')
    list_filter = ('vendor',)
    readonly_fields = ('vendor', 'category', 'created', 'modified')


class MappingAdmin(admin.ModelAdmin):
    list_display = ('mapping_key', 'mapping_type', 'mapping_aliases')
    readonly_fields = ('mapping_key', 'mapping_type')


admin.site.register(get_model('theimp', 'Product'), ProductAdmin)
admin.site.register(get_model('theimp', 'Vendor'), VendorAdmin)
admin.site.register(get_model('theimp', 'BrandMapping'), BrandMappingAdmin)
admin.site.register(get_model('theimp', 'CategoryMapping'), CategoryMappingAdmin)
admin.site.register(get_model('theimp', 'Mapping'), MappingAdmin)
admin.site.register(get_model('theimp', 'Brand'))
admin.site.register(get_model('theimp', 'Category'))
