from django.core.management.base import BaseCommand
from django.db.models import get_model
import logging
import datetime
import optparse


logger = logging.getLogger('dashboard')


class Command(BaseCommand):
    args = ''
    help = 'Temporary command to fix those sales from ASOS that has no user or Placement asigned'
    option_list = BaseCommand.option_list + (
        optparse.make_option('--vendor',
            action='store',
            dest='vendor',
            help='Insert vendor name where sales are originated from',
            default= None,
        ),
        optparse.make_option('--user',
            action='store',
            dest='user',
            help='Insert user id to assigned to the sales',
            default= None,
        ),
    )

    def handle(self, *args, **options):
        vendor_name = options.get('vendor')
        user_id = options.get('user')

        vendor = None
        user = None

        if vendor_name and user_id:
            logger.debug("Retrieve User and Vendor objects for user id %s and vendor name %s" % (user_id, vendor_name))
            # Get vendor and user objects
            try:
                vendor = get_model('apparel', 'Vendor').objects.get(name=vendor_name) #TODO pasar vendor y user como parametros
                user = get_model('profile', 'User').objects.get(id=user_id) # 29043 user id for MenWith in production
            except get_model('apparel', 'Vendor').DoesNotExist:
                logger.warning("Vendor ASOS does not exist")
            except get_model('profile', 'User').DoesNotExist:
                logger.warning("User does not exist")
        else:
            logger.warning("User id and/or vendor name have not being passed as parameters")

        # If vendor and user exist
        if vendor and user:
            query_date = datetime.date(2015, 10, 1) # From October 2015

            # Get all sales from ASOS/Zanox from October 1st, 2015 for placement unknown and user 0
            zanox_sales = get_model('dashboard', 'Sale').objects.filter(user_id=0, vendor=vendor, placement='Unknown',
                                                                        sale_date__gte=query_date, affiliate="Zanox")
            logger.debug("Found %s sales from ASOS" % len(zanox_sales))

            for sale in zanox_sales:
                logger.debug("Updating sale %s" % sale.id)

                # Remove existent earnings
                for earning in get_model('dashboard', 'UserEarning').objects.filter(sale=sale):
                    logger.debug("Removing earning %s" % earning.id)
                    earning.delete()
                # Update sale user and placement
                sale.user_id = user.id
                sale.placement = "Ext-Link"
                sale.save()

                # Log amount of new earnings that have been created for the given sale
                new_earnings = get_model('dashboard', 'UserEarning').objects.filter(sale=sale)
                logger.debug("Sale %s updated, %s earnings were created" % (sale.id, len(new_earnings)))
