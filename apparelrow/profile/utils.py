import time
import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.loading import get_model
from django.template.defaultfilters import slugify
from django.core.urlresolvers import reverse, resolve
from django.http import HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect

import facebook


FB_USER_SESSION_KEY = '_fb_user'
FB_USER_EXPIRES_SESSION_KEY = '_fb_user_expires'

class FacebookAccessor(object):
    """
    Simple accessor object for the Facebook user.
    """
    def __init__(self, user):
        self.user = user
        self.uid = user['uid']
        self.access_token = user['access_token']
        self.graph = facebook.GraphAPI(self.access_token)

def get_facebook_user(request):
    """
    Attempt to find a facebook user using a cookie. Cache fb_user in
    session.
    """
    fb_user = request.session.get(FB_USER_SESSION_KEY)
    expires = request.session.get(FB_USER_EXPIRES_SESSION_KEY)
    if not fb_user or expires < time.time():
        fb_user = facebook.get_user_from_cookie(request.COOKIES, settings.FACEBOOK_APP_ID, settings.FACEBOOK_SECRET_KEY)
        if fb_user:
            try:
                extended_user = facebook.GraphAPI(fb_user['access_token']).extend_access_token(settings.FACEBOOK_APP_ID, settings.FACEBOOK_SECRET_KEY)
                fb_user.update(extended_user)
            except facebook.GraphAPIError:
                pass

            expires = time.time() + int(fb_user['expires'])

            request.session[FB_USER_SESSION_KEY] = fb_user
            request.session[FB_USER_EXPIRES_SESSION_KEY] = expires

            get_user_model().objects.filter(username=fb_user['uid']).update(
                facebook_access_token=fb_user['access_token'],
                facebook_access_token_expire=datetime.datetime.fromtimestamp(expires)
            )

    return FacebookAccessor(fb_user) if fb_user else None


def slugify_unique(value, model, slugfield="slug"):
        suffix = 0
        potential = base = slugify(value)
        while True:
            if suffix:
                potential = '-'.join([base, str(suffix)])
            if not model.objects.filter(**{slugfield: potential}).count():
                return potential
            suffix += 1


def get_current_user(view_func):
    """
    """
    def _decorator(request, slug=None, *args, **kwargs):
        if not slug:
            if not request.user.is_authenticated():
                return HttpResponseRedirect('%s?next=%s' % (settings.LOGIN_URL, request.path))

            user = request.user
        else:
            try:
                user = get_user_model().objects.get(slug=slug)
            except get_user_model().DoesNotExist:
                user = get_user_model().objects.get(username=slug)
                if user.slug:
                    url_result = resolve(request.path)

                    return HttpResponsePermanentRedirect(reverse(url_result.url_name, args=[user.slug]))

        return view_func(request, user, *args, **kwargs)

    _decorator.__name__ = view_func.__name__
    _decorator.__dict__ = view_func.__dict__
    _decorator.__doc__  = view_func.__doc__

    return _decorator
