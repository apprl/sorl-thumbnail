import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.comments.models import Comment
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from django.template.loader import render_to_string
from django.middleware import csrf

from apparel.models import Product
from profile.models import Follow, ApparelProfile
from apparel.views import get_top_looks_in_network, get_top_products_in_network
from activity_feed.models import Activity, ActivityFeed

class ActivityFeedHTML:

    def __init__(self, request, queryset):
        self.request = request
        self.queryset = queryset

    def __len__(self):
        return len(self.queryset)

    def __getitem__(self, k):
        data = []
        for result in self.queryset[k]:
            # Comments
            # TODO: only generate comments if it is a single object
            comments = Comment.objects.filter(content_type=result.content_type, object_pk=result.object_id, is_public=True, is_removed=False) \
                                      .order_by('-submit_date') \
                                      .select_related('user', 'user__profile')[:2]
            comments =  list(reversed(comments))

            template_name = 'activity_feed/verbs/%s.html' % (result.verb,)
            data.append(render_to_string(template_name, {'user': self.request.user,
                                                         'current_user': self.request.user,
                                                         'verb': result.verb,
                                                         'created': result.created,
                                                         'objects': [result.activity_object],
                                                         'users': [result.user],
                                                         'comments': comments,
                                                         'csrf_token': csrf.get_token(self.request),
                                                         'CACHE_TIMEOUT': 10,
                                                         'LANGUAGE_CODE': self.request.LANGUAGE_CODE}))

        return data

@login_required
def user_feed(request):
    profile = request.user.get_profile()
    #profile.updates_last_visit = datetime.datetime.now()
    #profile.save()

    htmlset = ActivityFeedHTML(request, ActivityFeed.objects.get_for_user(profile))
    paginator = Paginator(htmlset, 5)

    page = request.GET.get('page')
    try:
        paged_result = paginator.page(page)
    except PageNotAnInteger:
        paged_result = paginator.page(1)
    except EmptyPage:
        paged_result = paginator.page(paginator.num_pages)

    if request.is_ajax():
        return render(request, 'activity_feed/feed.html', {
            'current_page': paged_result
        })

    popular_brands = ApparelProfile.objects.filter(user__is_active=True, is_brand=True).order_by('-followers_count')[:5]

    return render(request, 'activity_feed/user_feed.html', {
            'current_page': paged_result,
            'next': request.get_full_path(),
            'popular_products': get_top_products_in_network(profile, 4),
            'popular_looks': get_top_looks_in_network(profile, 3),
            'popular_brands': popular_brands,
        })
