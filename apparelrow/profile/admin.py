from django.contrib import admin

from profile.models import ApparelProfile
from profile.models import Follow
from profile.models import NotificationCache

class ApparelProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'brand', 'slug', 'is_brand', 'language', 'followers_count',)
    list_filter = ('is_brand',)
    search_fields = ('name',)
    raw_id_fields = ('user', 'brand')

admin.site.register(ApparelProfile, ApparelProfileAdmin)

admin.site.register(NotificationCache)

class FollowAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified')
    raw_id_fields = ['user', 'user_follow']
    list_display = ('user', 'user_follow', 'created', 'modified', 'active')
    list_filter = ('active',)

admin.site.register(Follow, FollowAdmin)
