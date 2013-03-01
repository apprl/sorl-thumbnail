from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models.loading import get_model
import facebook

from profile.notifications import process_facebook_friends
from profile.signals import user_created_with_email
from profile.utils import slugify_unique

FB_GENDER_MAP = { 'male': 'M', 'female': 'W' }

class FacebookProfileBackend(ModelBackend):
    """
    Authenticate a facebook user and autopopulate facebook data into the
    user's profile.

    """
    def authenticate(self, fb_uid=None, fb_graphtoken=None):
        """
        If we receive a facebook uid then the cookie has already been
        validated.
        """
        if fb_uid and fb_graphtoken:
            user, created = get_user_model().objects.get_or_create(username=fb_uid)
            graph = facebook.GraphAPI(fb_graphtoken)
            me = graph.get_object('me')

            if created:
                # It would be nice to replace this with an asynchronous request
                if me:
                    if me.get('first_name'):
                        user.first_name = me['first_name']
                    if me.get('last_name'):
                        user.last_name = me['last_name']
                    if me.get('email'):
                        user.email = me['email']
                    user.save()

                    profile = user.get_profile()
                    if me.get('name'):
                        profile.name = me.get('name')
                    profile.slug = slugify_unique(profile.display_name_live, profile.__class__)
                    profile.save()

                    process_facebook_friends.delay(user, fb_graphtoken)
                    user_created_with_email.send(sender=get_user_model(), user=user)

            profile = user.get_profile()
            if profile.gender is None:
                if me.get('gender'):
                    if me['gender'] in FB_GENDER_MAP:
                        profile.gender = FB_GENDER_MAP[me['gender']]
                        profile.save()

            return user

        return None
