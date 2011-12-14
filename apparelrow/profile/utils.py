from django.conf import settings
import facebook
import time

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
    if not fb_user or expires < time.time() + 2:
        fb_user = facebook.get_user_from_cookie(request.COOKIES, settings.FACEBOOK_APP_ID, settings.FACEBOOK_SECRET_KEY)
        if fb_user:
            request.session[FB_USER_SESSION_KEY] = fb_user
            request.session[FB_USER_EXPIRES_SESSION_KEY] = time.time() + int(fb_user['expires'])

    return FacebookAccessor(fb_user) if fb_user else None
