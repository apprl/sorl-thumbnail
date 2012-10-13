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
from activity_feed.models import ActivityFeed

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
            comments =  list(reversed(Comment.objects.filter(content_type=result.content_type, object_pk=result.object_id, is_public=True, is_removed=False).order_by('-submit_date').select_related('user', 'user__profile')[:2]))

            data.append(render_to_string('activity_feed/verbs/%s.html' % (result.verb,), {'object': result,
                                                                                          'comments': comments,
                                                                                          'user': self.request.user,
                                                                                          'csrf_token': csrf.get_token(self.request),
                                                                                          'CACHE_TIMEOUT': 10,
                                                                                          'LANGUAGE_CODE': self.request.LANGUAGE_CODE}))
        return data

@login_required
def user_feed(request):
    profile = request.user.get_profile()
    profile.updates_last_visit = datetime.datetime.now()
    profile.save()

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





    ## Update the time we last checked "friends updates"


    #paged_result, pagination = get_pagination_page(queryset,
            #FAVORITES_PAGE_SIZE, request.GET.get('page', 1), 1, 2)

    #if request.is_ajax():
        #return render_to_response('apparel/fragments/activity/list.html', {
            #'pagination': pagination,
            #'current_page': paged_result
        #}, context_instance=RequestContext(request))

    #return render_to_response('apparel/user_home.html', {
            #'pagination': pagination,
            #'current_page': paged_result,
            #'next': request.get_full_path(),
            #'profile': profile,
            #'popular_looks_in_network': get_top_looks_in_network(request.user, limit=limit),
            #'popular_products_in_network': popular_products
        #}, context_instance=RequestContext(request))
