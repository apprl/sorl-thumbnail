from django.contrib import admin
from profile.models import ApparelProfile

class ApparelProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'language', 'first_visit', 'followers_count',)

admin.site.register(ApparelProfile, ApparelProfileAdmin)
