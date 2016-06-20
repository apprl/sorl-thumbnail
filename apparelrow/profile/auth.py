from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models.loading import get_model
import facebook

from apparelrow.profile.notifications import process_facebook_friends
from apparelrow.profile.utils import slugify_unique

from apparelrow.apparel.utils import get_ga_cookie_cid
from apparelrow.apparel.tasks import google_analytics_event

FB_GENDER_MAP = { 'male': 'M', 'female': 'W' }


class UsernameAndEmailBackend(ModelBackend):
    def authenticate(self, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username and '@' in username:
            try:
                user = UserModel._default_manager.get(email=username)
                if user.check_password(password):
                    return user
            except UserModel.DoesNotExist:
                pass
            except UserModel.MultipleObjectsReturned:
                pass

        return super(UsernameAndEmailBackend, self).authenticate(username=username,
                                                                 password=password,
                                                                 **kwargs)


class FacebookProfileBackend(ModelBackend):
    """
    Authenticate a facebook user and autopopulate facebook data into the
    user's profile.

    """
    def authenticate(self, fb_uid=None, fb_graphtoken=None, request=None):
        """
        If we receive a facebook uid then the cookie has already been
        validated.
        """
        if fb_uid and fb_graphtoken:
            graph = facebook.GraphAPI(fb_graphtoken)
            me = graph.get_object('me')

            defaults = {'username': fb_uid}
            if me:
                if me.get('username'):
                    defaults['username'] = me['username']
                if me.get('first_name'):
                    defaults['first_name'] = me['first_name']
                if me.get('last_name'):
                    defaults['last_name'] = me['last_name']
                if me.get('email'):
                    defaults['email'] = me['email']
                if me.get('name'):
                    defaults['name'] = me['name']

            if 'email' in defaults:
                if get_user_model().objects.filter(email=defaults['email']).exists():
                    user = get_user_model().objects.filter(email=defaults['email'])[0]
                    if not user.facebook_user_id:
                        user.facebook_user_id = fb_uid
                        process_facebook_friends.delay(user, fb_graphtoken)
                else:
                    user, created = get_user_model().objects.get_or_create(facebook_user_id=fb_uid, defaults=defaults)
                    if created:
                        google_analytics_event.delay(get_ga_cookie_cid(request), 'Member', 'Signup', user.slug)
                        process_facebook_friends.delay(user, fb_graphtoken)

                if user.gender is None:
                    if me.get('gender'):
                        if me['gender'] in FB_GENDER_MAP:
                            user.gender = FB_GENDER_MAP[me['gender']]
                            user.save()

                return user

        return None
