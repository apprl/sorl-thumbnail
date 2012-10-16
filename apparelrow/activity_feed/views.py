import datetime
import json

from django.contrib.auth.decorators import login_required
from django.contrib.comments.models import Comment
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from django.template.loader import render_to_string
from django.middleware import csrf
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

from apparel.models import Product, Look
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
        return_data = []
        for result in self.queryset[k]:
            context = {'current_user': self.request.user,
                       'verb': result.verb,
                       'created': result.created,
                       'objects': [result.activity_object],
                       'users': [result.user],
                       'csrf_token': csrf.get_token(self.request),
                       'CACHE_TIMEOUT': 10,
                       'LANGUAGE_CODE': self.request.LANGUAGE_CODE}

            # Comments
            # TODO: only generate comments if it is a single object
            comments = Comment.objects.filter(content_type=result.content_type, object_pk=result.object_id, is_public=True, is_removed=False) \
                                      .order_by('-submit_date') \
                                      .select_related('user', 'user__profile')[:2]
            context['comment_count'] = Comment.objects.filter(content_type=result.content_type, object_pk=result.object_id, is_public=True, is_removed=False).count()
            context['comments'] =  list(reversed(comments))

            context['enable_comments'] = False
            if context['comments'] or result.verb in ['like_product', 'like_look', 'create']:
                context['enable_comments'] = True

            # Data (TODO: probably temporary until we use proper aggregation)
            if result.data:
                data = json.loads(result.data)

                # TODO: ugly hack, see todo above
                if 'products' in data and result.verb == 'add_product':
                    context['objects'] = Product.objects.filter(id__in=data['products'])
                    context['total_objects_count'] = data['product_count']
                    context['remaining_count'] = data['product_count'] - len(context['objects'])

            template_name = 'activity_feed/verbs/%s.html' % (result.verb,)
            rendered_template = render_to_string(template_name, context)
            return_data.append(rendered_template)

        return return_data

def public_feed(request):
    htmlset = ActivityFeedHTML(request, Activity.objects.all())
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

    popular_products = Product.valid_objects.order_by('-popularity')[:4]
    popular_looks = Look.objects.order_by('-popularity', '-created')[:3]
    popular_brands = ApparelProfile.objects.filter(user__is_active=True, is_brand=True).order_by('-followers_count')[:5]
    popular_members = ApparelProfile.objects.filter(user__is_active=True, is_brand=False).order_by('-followers_count')[:5]

    return render(request, 'activity_feed/public_feed.html', {
            'current_page': paged_result,
            'next': request.get_full_path(),
            'popular_products': popular_products,
            'popular_looks': popular_looks,
            'popular_brands': popular_brands,
            'popular_members': popular_members,
        })

def user_feed(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('public_feed'))

    profile = request.user.get_profile()
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
