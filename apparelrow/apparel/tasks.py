import logging
import datetime
import unicodedata
import os
import os.path
import string
import decimal
import time
import itertools

from django.conf import settings
from django.core.cache import get_cache
from django.core.management import call_command
from django.core.files import storage
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.db.models import Q
from django.db.models.loading import get_model
from django.template.loader import render_to_string
from django.utils.encoding import smart_unicode

from cStringIO import StringIO

from PIL import Image

from sorl.thumbnail import get_thumbnail, delete as sorl_delete

from mailsnake import MailSnake
from mailsnake.exceptions import MailSnakeException
from celery.task import task, periodic_task, PeriodicTask
from celery.schedules import crontab
import requests

from apparelrow.apparel.utils import send_google_analytics_event

logger = logging.getLogger('apparel.tasks')


@task(name='apparelrow.apparel.tasks.google_analytics_event', max_retries=1, ignore_result=True)
def google_analytics_event(cid, category, action, label=None, value=None):
    send_google_analytics_event(cid, category, action, label, value)


@task(name='apparelrow.apparel.tasks.empty_embed_shop_cache', max_retries=5, ignore_result=True)
def empty_embed_shop_cache(embed_shop_id):
    """
        Invalidate embedded shops 2.0 from cache
    """
    get_cache('nginx').delete(reverse('embed-shop', args=[embed_shop_id]))

# @task(name='apparelrow.apparel.tasks.empty_embed_shop_cache', max_retries=5, ignore_result=True)
# def empty_embed_shop_cache(embed_shop_id):
#    for x in itertools.product((x[0] for x in settings.LANGUAGES), ['A', 'M', 'W']):
#        get_cache('nginx').delete(reverse('shop-embed', args=[embed_shop_id, x[0], x[1]]))

@task(name='apparelrow.apparel.tasks.empty_embed_look_cache', max_retries=5, ignore_result=True)
def empty_embed_look_cache(look_slug):
    get_cache('nginx').delete(reverse('look-embed', args=[look_slug]))
    for look_embed in get_model('apparel', 'LookEmbed').objects.filter(look__slug=look_slug):
        get_cache('nginx').delete(reverse('look-embed-identifier', args=[look_embed.identifier, look_slug]))


@task(name='apparelrow.apparel.tasks.look_popularity', max_retries=5, ignore_result=True)
def look_popularity(look):
    LookLike = get_model('apparel', 'LookLike')

    like_count = LookLike.objects.filter(look=look, active=True).count()
    popularity = decimal.Decimal(like_count / 100000000.0)

    two_week_interval = datetime.datetime.now() - datetime.timedelta(weeks=2)
    like_count = LookLike.objects.filter(look=look,
                                         active=True,
                                         created__gte=two_week_interval).count()

    timedelta = datetime.datetime.now() - look.created
    item_half_hour_age =  (timedelta.days * 86400 + timedelta.seconds) / 7200
    if item_half_hour_age > 0:
        popularity += decimal.Decimal(like_count / float(pow(item_half_hour_age, 1.53)))

    look.popularity = popularity
    look.save(update_fields=['popularity'])

    return look.popularity


@task(name='apparelrow.apparel.tasks.product_popularity', max_retries=5, ignore_result=True)
def product_popularity(product):
    ProductClick = get_model('statistics', 'ProductClick')
    ProductLike = get_model('apparel', 'ProductLike')

    click_count = 0
    try:
        click_count = ProductClick.objects.get(product=product).click_count
    except ProductClick.MultipleObjectsReturned:
        click_count = ProductClick.objects.filter(product=product)[:1][0].click_count
        logger.warning('Duplicate item found in ProductClick: %s:%s' % (product.pk,
                                                                        product.slug))
    except ProductClick.DoesNotExist:
        pass

    two_week_interval = datetime.datetime.now() - datetime.timedelta(weeks=2)
    like_count = ProductLike.objects.filter(product=product,
                                            active=True,
                                            created__gte=two_week_interval).count()

    total_count = like_count + 1 * click_count

    timedelta = datetime.datetime.now() - product.date_added
    item_half_hour_age =  (timedelta.days * 86400 + timedelta.seconds) / 7200
    if item_half_hour_age > 0:
        product.popularity = decimal.Decimal(str(total_count / pow(item_half_hour_age, 1.53)))
        product.save(update_fields=['popularity'])
    elif product.popularity > decimal.Decimal(0):
        product.popularity = decimal.Decimal(0)
        product.save(update_fields=['popularity'])

    return product.popularity


@periodic_task(name='apparel.email.mailchimp_subscribe_members', run_every=crontab(minute='0', hour='6,18'), max_retries=1, ignore_result=True)
def mailchimp_subscribe_members():
    if not settings.DEBUG:
        batch = []
        for user in get_user_model().objects.exclude(Q(email__isnull=True) | Q(email__exact='')).iterator():
            batch.append({'EMAIL': user.email,
                          'FNAME': user.first_name,
                          'LNAME': user.last_name,
                          'GENDER': user.gender,
                          'PUBLISHER': int(user.is_partner),
                          'TOP_PUB': int(user.is_top_partner),
                          'USERID': user.pk})

        mailchimp = MailSnake(settings.MAILCHIMP_API_KEY)
        mailchimp.listBatchSubscribe(id=settings.MAILCHIMP_MEMBER_LIST, double_optin=False, update_existing=True, batch=batch)

        batch = []
        for user in get_user_model().objects.filter(is_partner=True).exclude(Q(email__isnull=True) | Q(email__exact='')).iterator():
            batch.append({'EMAIL': user.email,
                          'FNAME': user.first_name,
                          'LNAME': user.last_name,
                          'GENDER': user.gender,
                          'PUBLISHER': int(user.is_partner),
                          'TOP_PUB': int(user.is_top_partner),
                          'USERID': user.pk})

        mailchimp = MailSnake(settings.MAILCHIMP_API_KEY)
        mailchimp.listBatchSubscribe(id=settings.MAILCHIMP_PUBLISHER_LIST, double_optin=False, update_existing=True, batch=batch)

        batch = []
        for user in get_user_model().objects.filter(newsletter=True) \
                                            .exclude(Q(email__isnull=True) | Q(email__exact='')) \
                                            .exclude(Q(first_name__isnull=True) | Q(first_name__exact='')) \
                                            .exclude(Q(last_name__isnull=True) | Q(last_name__exact='')) \
                                            .iterator():
            batch.append({'EMAIL': user.email,
                          'FNAME': user.first_name,
                          'LNAME': user.last_name,
                          'GENDER': user.gender,
                          'PUBLISHER': int(user.is_partner)})

        mailchimp = MailSnake(settings.MAILCHIMP_API_KEY)
        mailchimp.listBatchSubscribe(id=settings.MAILCHIMP_NEWSLETTER_LIST, double_optin=False, update_existing=True, batch=batch)


@task(name='apparel.email.mailchimp_subscribe', max_retries=5, ignore_result=True)
def mailchimp_subscribe(user):
    try:
        mailchimp = MailSnake(settings.MAILCHIMP_API_KEY)
        mailchimp.listSubscribe(id=settings.MAILCHIMP_NEWSLETTER_LIST,
                                email_address=user.email,
                                merge_vars={'EMAIL': user.email, 'FNAME': user.first_name, 'LNAME': user.last_name, 'GENDER': user.gender, 'PUBLISHER': int(user.is_partner)},
                                double_optin=False,
                                update_existing=True,
                                send_welcome=False)
    except MailSnakeException, e:
        logger.error('Could not subscribe user to mailchimp: %s' % (e,))

@task(name='apparel.email.mailchimp_unsubscribe', max_retries=5, ignore_result=True)
def mailchimp_unsubscribe(user, delete=False):
    try:
        mailchimp = MailSnake(settings.MAILCHIMP_API_KEY)
        mailchimp.listUnsubscribe(id=settings.MAILCHIMP_NEWSLETTER_LIST,
                                  email_address=user.email,
                                  delete_member=delete,
                                  send_goodbye=False,
                                  send_notify=False)
    except MailSnakeException, e:
        logger.error('Could not unsubscribe user from mailchimp: %s' % (e,))


ACTION_TRANSLATION = {'like': 'og.likes', 'follow': 'og.follows', 'create': '%s:create' % (settings.FACEBOOK_OG_TYPE,)}

@task(name='apparel.facebook_push_graph', max_retries=5, ignore_result=True)
def facebook_push_graph(user_id, access_token, action, object_type, object_url):
    url = 'https://graph.facebook.com/me/%s' % (ACTION_TRANSLATION[action],)
    response = requests.post(url, data={object_type: object_url, 'access_token': access_token})
    data = response.json()

    logger.info(data)

    if 'id' in data:
        get_model('apparel', 'FacebookAction').objects.get_or_create(user_id=user_id, action=action, action_id=data['id'], object_type=object_type, object_url=object_url)
    elif 'error' in data and data['error']['code'] == 2:
        facebook_push_graph.retry(countdown=15)

@task(name='apparel.facebook_pull_graph', max_retries=1, ignore_result=True)
def facebook_pull_graph(user_id, access_token, action, object_type, object_url):
    try:
        facebook_action = get_model('apparel', 'FacebookAction').objects.get(user_id=user_id, action=action, object_type=object_type, object_url=object_url)
        facebook_action.delete()
        url = 'https://graph.facebook.com/%s' % (facebook_action.action_id,)
        response = requests.delete(url, data={'access_token': access_token})
        logger.info(response.json())
    except get_model('apparel', 'FacebookAction').DoesNotExist:
        logger.warning('No facebook action_id found for uid=%s action=%s type=%s' % (user_id, action, object_type))


# XXX: offline
#@periodic_task(name='apparel.tasks.update_vendor_data', run_every=crontab(minute='0,15,30,45'), max_retries=1, ignore_result=True)
def update_vendor_data():
    """
    Updates vendor data every half hour.
    """
    timestamp = datetime.datetime.now() - datetime.timedelta(minutes=20)
    for vendor_brand in get_model('apparel', 'VendorBrand').objects.filter(modified__gt=timestamp).iterator():
        if vendor_brand.brand:
            for product in get_model('apparel', 'Product').objects.filter(vendorproduct__vendor_brand_id=vendor_brand.id).iterator():
                if product.manufacturer_id != vendor_brand.brand_id:
                    product.manufacturer_id = vendor_brand.brand_id
                    product.save()
        else:
            queryset = get_model('apparel', 'Product').objects.filter(vendorproduct__vendor_brand_id=vendor_brand.id, manufacturer__isnull=False)
            for product in queryset:
                product.manufacturer_id = None
                product.save()

    for vendor_category in get_model('apparel', 'VendorCategory').objects.filter(modified__gt=timestamp).iterator():
        if vendor_category.category:
            queryset = get_model('apparel', 'Product').objects.filter(vendorproduct__vendor_category=vendor_category)
            for product in queryset:
                product.category = self.category
                product.published = True
                product.save()
        else:
            queryset = get_model('apparel', 'Product').objects.filter(vendorproduct__vendor_category=vendor_category, category__isnull=False)
            for product in queryset:
                product.category = None
                product.save()


# XXX: offline
#@periodic_task(name='apparel.tasks.generate_brand_list_template', run_every=crontab(minute='34'), max_retries=1, ignore_result=True)
def generate_brand_list_template():
    for gender in ['M', 'W']:
        alphabet = [u'0-9'] + list(unicode(string.ascii_lowercase))
        brands = []
        brands_mapper = {}
        for index, alpha in enumerate(alphabet):
            brands_mapper[alpha] = index
            brands.append([alpha, []])

        query_arguments = {'fl': 'manufacturer_id',
                           'fq': ['django_ct:apparel.product', 'availability:true', 'published:true', 'gender:(U OR %s)' % (gender,)],
                           'start': 0,
                           'rows': -1,
                           'group': 'true',
                           'group.field': 'manufacturer_id'}
        brand_ids = []
        from apparelrow.apparel.search import ApparelSearch
        for brand in ApparelSearch('*:*', **query_arguments).get_grouped().get('manufacturer_id', {}).get('groups', []):
            brand_ids.append(int(brand.get('groupValue', 0)))

        for item in get_user_model().objects.filter(brand__id__in=brand_ids).order_by('brand__name'):
            normalized_name = unicodedata.normalize('NFKD', smart_unicode(item.brand.name)).lower()
            for index, char in enumerate(normalized_name):
                if char in alphabet:
                    brands[brands_mapper[char]][1].append(item)
                    break
                elif char.isdigit():
                    brands[brands_mapper[u'0-9']][1].append(item)
                    break

        if gender == 'M':
            template_name = 'brand_list_men.html'
            template_temp_name = 'brand_list_men.html.tmp'
        else:
            template_name = 'brand_list_women.html'
            template_temp_name = 'brand_list_women.html.tmp'

        template_string = render_to_string('apparel/brand_list_generator.html', {'brands': brands})
        temp_filename = os.path.join(settings.PROJECT_ROOT, 'templates', 'apparel', 'generated', template_temp_name)
        filename = os.path.join(settings.PROJECT_ROOT, 'templates', 'apparel', 'generated', template_name)
        open(temp_filename, 'w').write(template_string.encode('utf-8'))
        os.rename(temp_filename, filename)


@task(name='apparelrow.apparel.tasks.build_static_look_image', max_retries=5, ignore_result=True)
def build_static_look_image(look_id):
    look = get_model('apparel', 'Look').objects.get(pk=look_id)

    image = Image.new('RGBA', settings.APPAREL_LOOK_SIZE, (255, 255, 255, 255))
    offset_left = 0
    offset_top = 0
    component_size = 40
    if look.display_with_component == 'P' and look.image:
        # Reuse photo image
        thumbnail = ''
        try:
            thumbnail = get_thumbnail(look.image, '694x524', upscale=False)
        except:
            logger.warning('No thumbnail found for %s '%look.image)
        # TODO: better solution?
        if thumbnail.url.startswith('http'):
            background = Image.open(StringIO(requests.get(thumbnail.url).content))
        else:
            background = Image.open(os.path.join(settings.MEDIA_ROOT, thumbnail.name))
        offset_left = (settings.APPAREL_LOOK_SIZE[0] - thumbnail.width) / 2
        offset_top = (settings.APPAREL_LOOK_SIZE[1] - thumbnail.height) / 2
        image.paste(background, (offset_left, offset_top))
        #look.width = thumbnail.width
        #look.height = thumbnail.height
    else:
        offset_left = (settings.APPAREL_LOOK_SIZE[0] - look.width)/2
        offset_top = (settings.APPAREL_LOOK_SIZE[1] - look.height)/2

    for component in look.display_components.order_by('z_index').all():
        if look.display_with_component == 'P':
            component_image = Image.open(finders.find('images/look-hotspot.png')).resize((component_size, component_size), Image.ANTIALIAS)
            if thumbnail.width < look.width or thumbnail.height < look.height:
                component.left = int(component.left*thumbnail.width/look.width)
                component.top = (component.top*thumbnail.height/look.height)
        else:
            if not component.product.product_image:
                continue

            # Reuse transparent thumbnail image
            try:
                thumbnail = get_thumbnail(component.product.product_image, '%s' % (settings.APPAREL_LOOK_MAX_SIZE,), format='PNG', transparent=True)
            except:
                logger.warning('No thumbnail found for %s '%component.product.product_image)

            # TODO: better solution?
            if thumbnail.url.startswith('http'):
                component_image = Image.open(StringIO(requests.get(thumbnail.url).content))
            else:
                component_image = Image.open(os.path.join(settings.MEDIA_ROOT, thumbnail.name))
            component_image = component_image.resize((component.width, component.height), Image.ANTIALIAS).convert('RGBA')
            if component.rotation:
                rotation = component_image.rotate(-component.rotation, Image.BICUBIC, 1)
                blank = Image.new('RGBA', rotation.size, (255, 255, 255, 0))
                component_image = Image.composite(rotation, blank, rotation)
            if component.flipped:
                component_image = component_image.transpose(Image.FLIP_LEFT_RIGHT)

        image.paste(component_image, (offset_left + component.left, offset_top + component.top), component_image)

    temp_handle = StringIO()
    image.save(temp_handle, 'JPEG', quality=99)
    temp_handle.seek(0)

    if look.static_image:
        sorl_delete(look.static_image)

    unique_tag = time.mktime(look.modified.timetuple())
    filename = '%s/static__%s_%d.jpg' % (settings.APPAREL_LOOK_IMAGE_ROOT, look.slug, unique_tag)
    storage.default_storage.save(filename, ContentFile(temp_handle.read()))
    look.static_image = filename

    # refresh thumbnail in mails
    try:
        get_thumbnail(look.static_image, '576', crop='noop')
    except:
        logger.warning('No thumbnail found for %s '%look.static_image)

    look.save(update_fields=['static_image', 'width', 'height', 'modified'])
