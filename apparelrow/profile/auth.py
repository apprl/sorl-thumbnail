from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend
from django.template.defaultfilters import slugify
import facebook

from profile.notifications import process_facebook_friends
from profile.signals import user_created_with_email

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
            user, created = User.objects.get_or_create(username=fb_uid)
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

                    process_facebook_friends.delay(user, fb_graphtoken)
                    user_created_with_email.send(sender=User, user=user)

                    profile = user.get_profile()
                    if me.get('name'):
                        profile.name = me.get('name')
                    profile.slug = slugify(profile.display_name)
                    profile.save()

                    # Follow all facebook friends
                    fids = [f['id'] for f in graph.get_connections('me', 'friends').get('data', [])]
                    for friend in ApparelProfile.objects.filter(user__username__in=fids):
                        follow, _ = Follow.objects.get_or_create(user=profile, user_follow=friend)

            profile = user.get_profile()
            if profile.gender is None:
                if me.get('gender'):
                    if me['gender'] in FB_GENDER_MAP:
                        profile.gender = FB_GENDER_MAP[me['gender']]
                        profile.save()

            return user

        return None
