import optparse
import datetime
import logging
from django.db.models.loading import get_model

from django.core.management.base import BaseCommand

logger = logging.getLogger('dashboard')


class Command(BaseCommand):
    args = ''
    help = 'Import dashboard data'
    option_list = BaseCommand.option_list + (
        optparse.make_option('--date',
            action='store',
            dest='date',
            help='Select a custom date in the format DD-MM-YYYY',
            default= (datetime.date.today() - datetime.timedelta(1)).strftime('%d-%m-%Y'),
        ),
    )

    def update(self, row):
        instance, created = get_model('dashboard', 'Sale').objects.get_or_create(affiliate=row['affiliate'], original_sale_id=row['original_sale_id'], defaults=row)

        if not created and instance.paid == get_model('dashboard', 'Sale').PAID_PENDING:
            for field in row.keys():
                setattr(instance, field, row.get(field))

            instance.save()

        return instance


    def handle(self, *args, **options):
        query_date = datetime.datetime.strptime(options.get('date'), '%d-%m-%Y')

        module = __import__('apparelrow.dashboard.importer.costperclick', fromlist = ['Importer'])
        instance = module.Importer()
        logger.info('Importing %s' % (instance.name,))
        for row in instance.get_data(query_date, None):
            sale_instance = self.update(row)