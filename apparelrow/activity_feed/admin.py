from django.contrib import admin

from apparelrow.activity_feed.models import Activity, ActivityFeed

class ActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'verb', 'content_type', 'object_id', 'created', 'modified', 'active')
    list_filter = ('verb',)
    raw_id_fields = ('user',)

admin.site.register(Activity, ActivityAdmin)

class ActivityFeedAdmin(admin.ModelAdmin):
    #list_display = ('owner', 'user', 'verb', 'content_type', 'object_id', 'created')
    list_display = ('owner', 'user', 'verb', 'activity_object', 'created')
    list_filter =('verb',)
    raw_id_fields = ('owner', 'user')

admin.site.register(ActivityFeed, ActivityFeedAdmin)
