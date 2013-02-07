from django.conf import settings
from django.db.models.loading import get_model
from django.template.defaultfilters import slugify
import facebook
import time
import datetime


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

            get_model('profile', 'ApparelProfile').objects.filter(user__username=fb_user['uid']).update(
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
