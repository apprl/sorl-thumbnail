from apparel.models import *
from django.contrib import admin
from mptt.admin import MpttModelAdmin

admin.site.register(Manufacturer)

admin.site.register(Product)

class CategoryAdmin(MpttModelAdmin):
    list_display = ('name',)

admin.site.register(Category, CategoryAdmin)

admin.site.register(Look)

admin.site.register(Option)


class OptionTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'type_group']


admin.site.register(OptionType, OptionTypeAdmin)
