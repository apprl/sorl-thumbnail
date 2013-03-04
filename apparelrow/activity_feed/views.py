import datetime
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.comments.models import Comment
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models.loading import get_model
from django.shortcuts import render
from django.template.loader import render_to_string
from django.middleware import csrf
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

import redis

from apparel.models import Product, Look
from apparel.views import get_top_looks_in_network, get_top_products_in_network
from activity_feed.models import Activity, ActivityFeed
from apparel.utils import get_gender_from_cookie

from activity_feed.tasks import get_feed_key

class ActivityFeedRender:
    """
    ActivityFeed render class.
    """

    def __init__(self, request, gender, user=None, private=False):
        self.request = request
        self.gender = gender
        self.user = user
        self.private = private
        self.r = redis.StrictRedis(host=settings.CELERY_REDIS_HOST,
                                   port=settings.CELERY_REDIS_PORT,
                                   db=settings.FEED_REDIS_DB)

    def __len__(self):
        item_count = 0
        try:
            return int(self.r.zcount(get_feed_key(self.user, self.gender, self.private), '-inf', '+inf'))
        except redis.exceptions.ConnectionError:
            return 0

        return item_count

    def __getitem__(self, k):
        rendered_templates = []

        try:
            results = self.r.zrevrange(get_feed_key(self.user, self.gender, self.private), k.start, k.stop - 1)
        except redis.exceptions.ConnectionError:
            return rendered_templates

        for result in results:
            result = json.loads(result)

            context = {'user': self.request.user, 'current_user': self.request.user,
                       'verb': result['v'],
                       'objects': [],
                       'csrf_token': csrf.get_token(self.request),
                       'CACHE_TIMEOUT': 60 * 60 * 24,
                       'LANGUAGE_CODE': self.request.LANGUAGE_CODE}

            activity_ids = result.get('a', [])[::-1]
            activities = Activity.objects.filter(pk__in=activity_ids[:4]) \
                                         .prefetch_related('activity_object') \
                                         .order_by('-created')

            if not activities:
                continue

            context['created'] = False
            for activity in activities:
                if context['created'] == False:
                    context['created'] = activity.created
                if activity.activity_object:
                    context['objects'].append(activity.activity_object)

            context['users'] = get_user_model().objects.filter(pk__in=result.get('u', []))
            context['total_objects'] = len(activity_ids)
            context['remaining_objects'] = len(activity_ids) - len(activity_ids[:4])

            if len(context['objects']) < 1:
                continue

            # Comments
            if context['total_objects'] == 1:
                context['comments'] = Comment.objects.filter(content_type=result['ct'],
                                                             object_pk=context['objects'][0].pk,
                                                             is_public=True,
                                                             is_removed=False)
                context['comment_count'] = context['comments'].count()
                context['comments'] = context['comments'].order_by('-submit_date').select_related('user')[:2]
                context['enable_comments'] = False
                if result['v'] in ['like_product', 'like_look', 'create']:
                    context['enable_comments'] = True

            template_name = 'activity_feed/verbs/%s.html' % (result['v'],)
            rendered_templates.append(render_to_string(template_name, context))

        return rendered_templates


def public_feed(request, gender=None):
    if not gender:
        gender_cookie = get_gender_from_cookie(request)
        if gender_cookie == 'W':
            return HttpResponseRedirect(reverse('public_feed-women'))
        elif gender_cookie == 'M':
            return HttpResponseRedirect(reverse('public_feed-men'))

    htmlset = ActivityFeedRender(request, gender, None)
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

    popular_products = Product.valid_objects.filter(gender__in=[gender, 'U']) \
                                            .order_by('-popularity')
    popular_looks = Look.published_objects.filter(gender__in=[gender, 'U']) \
                                          .order_by('-popularity', '-created')
    popular_brands = get_user_model().objects.filter(is_active=True, is_brand=True) \
                                             .order_by('-followers_count')
    popular_members = get_user_model().objects.filter(is_active=True, is_brand=False, gender=gender) \
                                              .order_by('-popularity', '-followers_count')
    if request.user and request.user.is_authenticated():
        follow_ids = get_model('profile', 'follow').objects.filter(user=request.user).values_list('user_follow', flat=True)
        popular_brands = popular_brands.exclude(id__in=follow_ids)
        popular_members = popular_members.exclude(id=request.user.pk).exclude(id__in=follow_ids)

    response = render(request, 'activity_feed/public_feed.html', {
            'current_page': paged_result,
            'next': request.get_full_path(),
            'popular_products': popular_products[:4],
            'popular_looks': popular_looks[:3],
            'popular_brands': popular_brands[:5],
            'popular_members': popular_members[:5],
        })
    response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=gender, max_age=365 * 24 * 60 * 60)

    return response


def dialog_user_feed(request):
    return render(request, 'activity_feed/dialog_user_feed.html', {'next': request.GET.get('next', '/')})


def user_feed(request, gender=None):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('public_feed'))

    if not gender:
        gender_cookie = get_gender_from_cookie(request)
        if gender_cookie == 'W':
            gender = 'W'
        elif gender_cookie == 'M':
            gender = 'M'
        else:
            gender = 'W'

    htmlset = ActivityFeedRender(request, gender, request.user)
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

    popular_brands = get_user_model().objects.filter(is_active=True, is_brand=True).order_by('-followers_count')
    popular_members = get_user_model().objects.filter(is_active=True, is_brand=False, gender=gender) \
                                              .order_by('-popularity', '-followers_count')

    if request.user and request.user.is_authenticated():
        follow_ids = get_model('profile', 'follow').objects.filter(user=request.user).values_list('user_follow', flat=True)
        popular_brands = popular_brands.exclude(id__in=follow_ids)
        popular_members = popular_members.exclude(id=request.user.pk).exclude(id__in=follow_ids)

    response = render(request, 'activity_feed/user_feed.html', {
            'current_page': paged_result,
            'next': request.get_full_path(),
            'popular_products': get_top_products_in_network(request.user, 4),
            'popular_looks': get_top_looks_in_network(request.user, 3),
            'popular_brands': popular_brands[:5],
            'popular_members': popular_members[:5],
        })
    response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=gender, max_age=365 * 24 * 60 * 60)

    return response
