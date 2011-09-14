from django.contrib import admin
from profile.models import ApparelProfile, NotificationCache

class ApparelProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'language', 'first_visit', 'followers_count',)

admin.site.register(ApparelProfile, ApparelProfileAdmin)

admin.site.register(NotificationCache)
