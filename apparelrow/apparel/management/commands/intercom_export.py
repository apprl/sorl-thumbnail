import os
import csv
import tempfile
import time
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from advertiser.models import Store


class Command(BaseCommand):
    args = ''
    help = 'Outputs CSV that can be imported into Intercom'

    def handle(self, *args, **options):
        handle, filename = tempfile.mkstemp()

        with open(filename, 'wb') as csvfile:
            writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
            writer.writerow(['id', 'name', 'email', 'date_joined', 'is_partner', 'is_store'])

            for user in get_user_model().objects.all():
                is_partner = user.is_partner
                is_store = Store.objects.filter(user__pk=user.pk).exists()

                writer.writerow([
                    user.pk,
                    user.name.encode('utf8') if user.name is not None else "",
                    user.email.encode('utf8'),
                    int(time.mktime(user.date_joined.timetuple())),
                    1 if is_partner else 0,
                    1 if is_store else 0
                ])

        with open(filename, 'r') as f:
            print f.read()

        os.remove(filename)