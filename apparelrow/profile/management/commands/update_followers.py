from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from actstream.models import Follow
from profile.models import ApparelProfile

class Command(BaseCommand):
    args = ''
    help = 'Updates followers count for every user'

    def handle(self, *args, **options):
        for user in User.objects.all():
            try:
                apparel_profile = user.get_profile()
                apparel_profile.followers_count = Follow.objects.filter(object_id=user.id).count()
                apparel_profile.save()
            except ApparelProfile.DoesNotExist:
                pass
