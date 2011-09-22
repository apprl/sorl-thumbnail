from beta.models import *
from django.contrib import admin

admin.site.register(Invite)
admin.site.register(Invitee)
admin.site.register(InvitePerUser)

class InviteRequestAdmin(admin.ModelAdmin):
    list_display = ['email', 'invitee']

admin.site.register(InviteRequest, InviteRequestAdmin)
