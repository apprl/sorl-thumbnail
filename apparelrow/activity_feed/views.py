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

from apparelrow.apparel.models import Product, Look
from apparelrow.apparel.utils import get_top_looks_in_network, get_top_products_in_network, get_gender_from_cookie, get_featured_activity_today

from apparelrow.activity_feed.models import Activity, ActivityFeed
from apparelrow.activity_feed.tasks import get_feed_key


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
        return render(request, 'activity_feed/fragments/feed_list.html', {
            'current_page': paged_result
        })

    response = render(request, 'activity_feed/feed_list.html', {
            'featured': get_featured_activity_today(),
            'current_page': paged_result,
            'next': request.get_full_path(),
        })
    response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=gender, max_age=365 * 24 * 60 * 60)

    return response


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
        return render(request, 'activity_feed/fragments/feed_list.html', {
            'current_page': paged_result
        })

    response = render(request, 'activity_feed/feed_list.html', {
            'featured': get_featured_activity_today(),
            'current_page': paged_result,
            'next': request.get_full_path(),
        })
    response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=gender, max_age=365 * 24 * 60 * 60)

    return response
