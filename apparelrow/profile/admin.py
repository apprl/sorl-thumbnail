from django.contrib import admin
from profile.models import ApparelProfile, NotificationCache

class ApparelProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'slug', 'is_brand', 'language', 'followers_count',)
    list_filter = ('is_brand',)
    search_fields = ('name',)

admin.site.register(ApparelProfile, ApparelProfileAdmin)

admin.site.register(NotificationCache)
