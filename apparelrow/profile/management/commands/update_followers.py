from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from apparelrow.profile.models import Follow

class Command(BaseCommand):
    args = ''
    help = 'Updates followers count for every user'

    def handle(self, *args, **options):
        for user in get_user_model().objects.all():
            user.followers_count = Follow.objects.filter(user__is_hidden=False, user_follow=user, active=True).count()
            user.save()
