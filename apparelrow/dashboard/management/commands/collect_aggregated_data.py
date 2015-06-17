import optparse
import datetime
import logging
from django.db.models.loading import get_model
from django.contrib.auth import get_user_model
import decimal
from django.db.models import Count
from django.views.generic import TemplateView
from django.core.urlresolvers import reverse

from apparelrow.dashboard.views import get_clicks_from_sale, get_product_thumbnail_and_link

from django.core.management.base import BaseCommand
from sorl.thumbnail import get_thumbnail
from sorl.thumbnail.fields import ImageField
from sorl.thumbnail.images import ThumbnailError

logger = logging.getLogger('dashboard')


class Command(BaseCommand):
    args = ''
    help = 'Import dashboard data'
    option_list = BaseCommand.option_list + (
        optparse.make_option('--date',
            action='store',
            dest='date',
            help='Select a custom date in the format YYYY-MM-DD',
            default= None,
        ),
    )

    def handle(self, *args, **options):
        Sale = get_model('dashboard', 'Sale')
        date = options.get('date')
        if not date:
            date = (datetime.date.today() - datetime.timedelta(1)).strftime('%Y-%m-%d')
        query_date = datetime.datetime.strptime(date, '%Y-%m-%d')

        start_date = datetime.datetime.combine(query_date, datetime.time(0, 0, 0, 0))
        end_date = datetime.datetime.combine(query_date, datetime.time(23, 59, 59, 999999))

        earnings = get_model('dashboard', 'UserEarning').objects.filter(date__range=(start_date, end_date))

        # Remove all existent data for the given date
        get_model('dashboard', 'AggregatedData').objects.filter(date=query_date.date()).delete()

        for row in earnings:
            earning_user = row.user
            user_id = 0 if not earning_user else earning_user.id
            user_name = 'APPRL' if user_id == 0 else ''
            user_username = 'APPRL' if user_id == 0 else ''
            if earning_user:
                user_name = earning_user.name if earning_user.name else ''
                user_username = earning_user.username if earning_user.username else ''

            instance, created = get_model('dashboard', 'AggregatedData').objects.\
                get_or_create(user_id=user_id, date=query_date.date(), type='aggregated_from_total',
                              user_name=user_name, user_username=user_username)

            earning_amount = decimal.Decimal(row.amount)

            # Aggregate earnings by type
            if row.user_earning_type in ('referral_sale_commission', 'referral_signup_commission'):
                instance.referral_sales += 1
                instance.referral_earnings += earning_amount
            elif row.user_earning_type == 'publisher_sale_commission':
                instance.sale_earnings += earning_amount
                instance.sales += 1
            elif row.user_earning_type == 'publisher_network_tribute':
                instance.network_sale_earnings += earning_amount
                instance.network_sales += 1
            elif row.user_earning_type == 'publisher_network_click_tribute':
                instance.network_click_earnings += earning_amount
                #instance.paid_clicks += get_clicks_from_sale(row.sale) ????
            elif row.user_earning_type == 'publisher_sale_click_commission':
                instance.click_earnings += earning_amount
                instance.paid_clicks += get_clicks_from_sale(row.sale)

            if user_id == 0 and row.user_earning_type == 'apprl_commission':
                if row.sale.type == Sale.COST_PER_CLICK:
                    instance.click_earnings += earning_amount
                elif row.sale.type == Sale.COST_PER_ORDER:
                    instance.sale_earnings += earning_amount

            # Aggregated data for products
            if row.from_product:
                product_instance, product_created = get_model('dashboard', 'AggregatedData').objects.\
                    get_or_create(user_id=user_id, date=query_date.date(), type='aggregated_from_product',
                                  aggregated_from_id=row.from_product.id, user_name=user_name, user_username=user_username)
                if row.user_earning_type in ('publisher_sale_commission', 'apprl_commission'):
                    product_instance.sale_earnings += row.amount
                    product_instance.sales += 1
                elif row.user_earning_type == 'referral_sale_commission':
                    product_instance.referral_sales += 1
                    product_instance.referral_earnings += earning_amount
                product_instance.aggregated_from_id = row.from_product.id
                product_instance.aggregated_from_name = row.from_product.product_name \
                    if row.from_product.product_name else ''
                product_instance.aggregated_from_slug = row.from_product.slug if row.from_product.slug else ''
                product_instance.save()

                if product_created:
                    clicks_count = get_model('statistics', 'ProductStat').objects.\
                        filter(user_id=user_id, vendor=row.sale.vendor.name, product=row.from_product.slug,
                               created__range=(start_date, end_date)).count()
                    if row.sale.vendor.is_cpc:
                        product_instance.paid_clicks = clicks_count
                    product_instance.total_clicks = clicks_count
                    product_instance.image, product_instance.link =  get_product_thumbnail_and_link(row.from_product)

                product_instance.save()

            # Aggregate data for publishers
            if row.user_earning_type in ('publisher_network_tribute', 'publisher_network_click_tribute'):
                publisher_instance, publisher_created = get_model('dashboard', 'AggregatedData').objects.\
                    get_or_create(user_id=user_id, date=query_date.date(), type='aggregated_from_publisher',
                                  aggregated_from_id=row.from_user.id, user_name=user_name, user_username=user_username)
                publisher_earning = get_model('dashboard', 'UserEarning').objects.\
                    get(user=row.from_user, date__range=(start_date, end_date), sale=row.sale)
                if publisher_created:
                    stats = get_model('statistics', 'ProductStat').objects.\
                        filter(created__range=(start_date, end_date), user_id=row.from_user.id).\
                        aggregate(clicks=Count('user_id'))
                    publisher_instance.total_clicks += stats['clicks']
                if row.user_earning_type == 'publisher_network_tribute':
                    publisher_instance.sale_earnings += publisher_earning.amount
                    publisher_instance.network_sale_earnings += row.amount
                    publisher_instance.network_sales += 1

                    if row.from_product:
                        product_instance, product_created = get_model('dashboard', 'AggregatedData').objects.\
                    get_or_create(user_id=user_id, date=query_date.date(), type='aggregated_from_product',
                                  aggregated_from_id=row.from_product.id, user_name=user_name, user_username=user_username)
                        product_instance.sale_earnings += publisher_earning.amount
                        product_instance.network_sale_earnings += earning_amount
                        product_instance.sale_plus_click_earnings += publisher_earning.amount
                        product_instance.total_network_earnings += earning_amount
                        product_instance.sales += 1
                        product_instance.aggregated_from_id = row.from_product.id
                        product_instance.aggregated_from_name = row.from_product.product_name \
                            if row.from_product.product_name else ''
                        product_instance.aggregated_from_slug = row.from_product.slug if row.from_product.slug else ''
                        product_instance.save()
                else:
                    publisher_instance.click_earnings += publisher_earning.amount
                    publisher_instance.network_click_earnings += row.amount
                    publisher_instance.paid_clicks += get_clicks_from_sale(row.sale)
                publisher_instance.sale_plus_click_earnings += publisher_earning.amount
                publisher_instance.total_network_earnings += row.amount
                publisher_instance.aggregated_from_id = row.from_user.id
                publisher_instance.aggregated_from_name = row.from_user.name if row.from_user.name else ''
                publisher_instance.aggregated_from_slug = row.from_user.username if row.from_user.username else ''
                publisher_instance.aggregated_from_link = reverse('profile-likes', args=[row.from_user.username])
                try:
                    publisher_instance.aggregated_from_image = get_thumbnail(ImageField().to_python(row.from_user.image), '50', crop='noop').url
                except ThumbnailError:
                    logger.warning('No profile image available for user %s.' % row.from_user.image)
                publisher_instance.save()

            instance.save()

        # Total clicks
        total_clicks = get_model('statistics', 'ProductStat').objects.\
            filter(created__range=(start_date, end_date)).values('user_id').\
            annotate(clicks=Count('user_id')).order_by('clicks')
        for row in total_clicks:
            instance, created = get_model('dashboard', 'AggregatedData').objects.\
                get_or_create(user_id=row['user_id'], date=query_date.date(), type='aggregated_from_total')
            if created and not (row['user_id'] == 0):
                row_user = get_user_model().objects.get(id=row['user_id'])
                instance.user_name = row_user.name if row_user.name else ''
                instance.user_username = row_user.username if row_user.username else ''
            instance.total_clicks = row['clicks']
            instance.save()

        # Aggregate ProductStat
        aggregated_product_stat = get_model('statistics', 'ProductStat').objects.\
            filter(created__range=(start_date, end_date)).values('user_id', 'product', 'vendor').\
            annotate(clicks=Count('product')).order_by('clicks')

        for row in aggregated_product_stat:
            product = get_model('apparel', 'Product').objects.get(slug=row['product'])
            vendor = get_model('apparel', 'Vendor').objects.get(name=row['vendor'])
            try:
                user = get_user_model().objects.get(id=user_id)
                if product:
                    product_instance, product_created = get_model('dashboard', 'AggregatedData').objects.\
                        get_or_create(user_id=row['user_id'], date=start_date.date(), type='aggregated_from_product',
                                      aggregated_from_id=product.id, aggregated_from_name=product.product_name,
                                      aggregated_from_slug=product.slug)

                    if product_created:
                        product_instance.image, product_instance.link =  get_product_thumbnail_and_link(product)
                        product_instance.user_name = user.name if user.name else ''
                        product_instance.user_username = user.username if user.username else ''

                    if vendor.is_cpc:
                        product_instance.paid_clicks += decimal.Decimal(row['clicks'])
                        try:
                            earning = get_model('dashboard', 'UserEarning').objects.get(user_id=row['user_id'],
                                                                              user_earning_type='publisher_sale_click_commission',
                                                                              date__range=(start_date, end_date))
                            clicks_number = get_clicks_from_sale(earning.sale)
                            click_cost = earning.amount / clicks_number
                            clicks = decimal.Decimal(row['clicks'])
                            product_instance.click_earnings += click_cost * clicks
                            product_instance.sale_plus_click_earnings += click_cost * clicks
                        except get_model('dashboard', 'UserEarning').DoesNotExist:
                            logger.warning("Click earning for user %s date %s does not exist" % (user.id, start_date.date()))

                    product_instance.total_clicks += decimal.Decimal(row['clicks'])
                    product_instance.save()

                    if user.owner_network:
                        owner = user.owner_network
                        ownerp_instance, ownerp_created = get_model('dashboard', 'AggregatedData').objects.\
                            get_or_create(user_id=owner.id, date=start_date.date(), type='aggregated_from_product',
                                      aggregated_from_id=product.id, aggregated_from_name=product.product_name,
                                      aggregated_from_slug=product.slug)
                        if ownerp_created:
                            ownerp_instance.image, ownerp_instance.link =  get_product_thumbnail_and_link(product)
                            ownerp_instance.user_name = owner.name if owner.name else ''
                            ownerp_instance.user_username = owner.username if owner.username else ''

                        if vendor.is_cpc:
                            ownerp_instance.paid_clicks += decimal.Decimal(row['clicks'])
                            try:
                                earning = get_model('dashboard', 'UserEarning').objects.get(user_id=owner.id,
                                                                                  user_earning_type='publisher_network_click_tribute',
                                                                                  date__range=(start_date, end_date))
                                clicks_number = get_clicks_from_sale(earning.sale)
                                click_cost = earning.amount / clicks_number
                                clicks = decimal.Decimal(row['clicks'])
                                ownerp_instance.click_earnings += click_cost * clicks
                                ownerp_instance.sale_plus_click_earnings += click_cost * clicks
                            except get_model('dashboard', 'UserEarning').DoesNotExist:
                                logger.warning("Click earning for user %s date %s does not exist" % (owner.id, start_date.date()))

                        ownerp_instance.total_clicks += decimal.Decimal(row['clicks'])
                        ownerp_instance.save()
            except get_user_model().DoesNotExist:
                logger.warning("User %s does not exist" % user_id)
                pass
        return