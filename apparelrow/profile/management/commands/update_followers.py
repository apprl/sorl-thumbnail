from django.core.management.base import BaseCommand, CommandError

from profile.models import ApparelProfile
from profile.models import Follow

class Command(BaseCommand):
    args = ''
    help = 'Updates followers count for every user'

    def handle(self, *args, **options):
        for profile in ApparelProfile.objects.all():
            profile.followers_count = Follow.objects.filter(user_follow=profile, active=True).count()
            profile.save()
