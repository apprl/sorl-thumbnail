from beta.models import *
from django.contrib import admin

admin.site.register(Invite)

class InviteeAdmin(admin.ModelAdmin):
    search_fields = ['email']
    list_display = ['email', 'invite', 'created', 'used_count', 'seen']
    ordering = ['email']

admin.site.register(Invitee, InviteeAdmin)

class InvitePerUserAdmin(admin.ModelAdmin):
    search_fields = ['user__name']
    list_display = ['user']
    ordering = ['user__name']

admin.site.register(InvitePerUser, InvitePerUserAdmin)

class InviteRequestAdmin(admin.ModelAdmin):
    list_display = ['email', 'invitee']
    ordering = ['email']

admin.site.register(InviteRequest, InviteRequestAdmin)
