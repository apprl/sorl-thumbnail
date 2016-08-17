import logging
import optparse
import time
from django.core.management.base import BaseCommand
from django.db.models.loading import get_model
from datetime import date, timedelta
from progressbar import ProgressBar, Percentage, Bar

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Sidenote, this job is for some reason not attached to the scheduler. Its run by crontab by user deploy on server admin.
    """

    args = ''
    help = 'Counts products for every parsed category'
    quarantine = 60
    option_list = BaseCommand.option_list + (
        optparse.make_option('--verbose',
            action='store_true',
            dest='verbose',
            help='Creating verbose progressbar output.',
            default= False,
        ),
    )

    def handle(self, *args, **options):
        logger.debug("Starting counting...")
        modified_since = date.today() - timedelta(days=self.quarantine)
        start = time.time()
        pbar = None
        if options.get("verbose"):
            maxval = get_model('theimp', 'CategoryMapping').objects.count()
            pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=maxval).start()

        for index, category in enumerate(self.get_category_mappings()):
            if pbar:
                pbar.update(index)

            products_counter = get_model('theimp', 'Product').objects.filter(category_mapping=category, modified__gt=modified_since).count()
            if category.products_counter != products_counter:
                category.products_counter = products_counter
                category.save()
        if pbar:
            pbar.finish()
        end = time.time()
        logger.debug("Finishing on %s seconds"%(end - start))

    def get_category_mappings(self):
        category_mappings = get_model('theimp', 'CategoryMapping').objects.all()
        for category in category_mappings.iterator():
            yield category