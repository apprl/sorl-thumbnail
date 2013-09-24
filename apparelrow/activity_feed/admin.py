from django.contrib import admin

from apparelrow.activity_feed.models import Activity, ActivityFeed

from datetime import date

from django.utils.translation import ugettext_lazy as _
from django.contrib.admin import SimpleListFilter

class HumanListFilter(SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('humans')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'human'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('yes', _('yes')),
            ('no', _('no')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or 'other')
        # to decide how to filter the queryset.
        if self.value() == 'yes':
            return queryset.filter(verb__in=['like_product', 'like_look', 'create', 'follow'])
        if self.value() == 'no':
            return queryset.filter(verb__in=['add_product', 'agg_product'])


class ActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'verb', 'content_type', 'object_id', 'created', 'modified', 'active', 'featured_date')
    list_filter = ('verb', 'featured_date', HumanListFilter)
    raw_id_fields = ('user',)

admin.site.register(Activity, ActivityAdmin)

class ActivityFeedAdmin(admin.ModelAdmin):
    #list_display = ('owner', 'user', 'verb', 'content_type', 'object_id', 'created')
    list_display = ('owner', 'user', 'verb', 'activity_object', 'created')
    list_filter =('verb',)
    raw_id_fields = ('owner', 'user')

admin.site.register(ActivityFeed, ActivityFeedAdmin)
