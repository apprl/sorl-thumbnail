import time
import datetime
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.utils.translation import ugettext
import facebook

from apparelrow.profile.tasks import send_welcome_email_task


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


def reset_facebook_user(request):
    if FB_USER_SESSION_KEY in request.session:
        del request.session[FB_USER_SESSION_KEY]

    if FB_USER_EXPIRES_SESSION_KEY in request.session:
        del request.session[FB_USER_EXPIRES_SESSION_KEY]


def get_facebook_user(request):
    """
    Attempt to find a facebook user using a cookie. Cache fb_user in
    session.
    """
    fb_user = request.session.get(FB_USER_SESSION_KEY)
    expires = request.session.get(FB_USER_EXPIRES_SESSION_KEY)
    if not fb_user or expires < time.time():
        try:
            fb_user = facebook.get_user_from_cookie(request.COOKIES, settings.FACEBOOK_APP_ID, settings.FACEBOOK_SECRET_KEY)
            if fb_user:
                try:
                    extended_user = facebook.GraphAPI(fb_user['access_token']).extend_access_token(settings.FACEBOOK_APP_ID, settings.FACEBOOK_SECRET_KEY)
                    fb_user.update(extended_user)
                except facebook.GraphAPIError as e:
                    logging.warning('Facebook GraphAPIError during extended access token attempt: %s' % (str(e),))

                expires = time.time() + int(fb_user['expires'])

                request.session[FB_USER_SESSION_KEY] = fb_user
                request.session[FB_USER_EXPIRES_SESSION_KEY] = expires

                get_user_model().objects.filter(facebook_user_id=fb_user['uid']).update(
                    facebook_access_token=fb_user['access_token'],
                    facebook_access_token_expire=datetime.datetime.fromtimestamp(expires)
                )
        except Exception, msg:
            logging.warning('Could not fetch facebook user: %s' % (msg))
            return None

    return FacebookAccessor(fb_user) if fb_user else None


def slugify_unique(value, model, slugfield='slug'):
    suffix = 0
    potential = base = slugify(value)
    while True:
        if suffix:
            potential = '-'.join([base, str(suffix)])
        if not model.objects.filter(**{slugfield: potential}).count():
            return potential
        suffix += 1

def send_welcome_mail(user):
    subject = ugettext(u'Welcome to Apprl %(name)s') % {'name': user.display_name}
    body = render_to_string('profile/email_welcome.html', {'name': user.display_name})
    send_welcome_email_task.delay(subject, body, user.email)
