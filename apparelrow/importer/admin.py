from django.contrib import admin
from django.forms.models import BaseInlineFormSet

from importer.models import *


# FIXME: 
#  To do for this:
#   1) Link listed ImportLog objects from the VendorFeed admin page to their respective page
#   2) Highlight ImportLog and ImportLogMessages who's status is error or failed
#   3) Enabling filtering on ImportLogMessage.status so that everything that requires attention
#      can be dealt with directly


class ImportLogMessageInline(admin.TabularInline):
    model = ImportLogMessage
    extra = 0
    can_delete = False
    readonly_fields = ('status', 'message', 'datetime',)
    
    # FIXME: Add CSS rules that makes the "message" field display as pre
    #class Media:
    #    css = {
    #        "all": ("imporrtstyles.css",)
    #    }

class ImportLogInline(admin.TabularInline):
    model = ImportLog
    extra = 0
    can_delete = False
    readonly_fields = ('imported_products', 'status', 'start_time', 'end_time',)


class ImportLogAdmin(admin.ModelAdmin):
    inlines = [
        ImportLogMessageInline
    ]
    readonly_fields = ('imported_products', 'start_time', 'end_time', 'status', 'vendor_feed',)


class VendorFeedAdmin(admin.ModelAdmin):
    inlines = [
        ImportLogInline
    ]


admin.site.register(VendorFeed, VendorFeedAdmin)
admin.site.register(ImportLog, ImportLogAdmin)
admin.site.register(ImportLogMessage)

