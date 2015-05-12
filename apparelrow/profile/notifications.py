import logging
import decimal
import HTMLParser
from celery.schedules import crontab
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.mail import EmailMultiAlternatives
from django.core.mail import EmailMessage
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.comments.models import Comment
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import get_language, activate
from django.core.urlresolvers import reverse
from django.utils.formats import number_format
from django.db.models.loading import get_model
from django.db.models import Q
from django.core.files.storage import DefaultStorage

from sorl.thumbnail import get_thumbnail
from django.templatetags.static import static
# for summaries
from datetime import timedelta
from django.utils import timezone

import facebook

from celery.task import task, periodic_task

from apparelrow.apparel.utils import currency_exchange


def is_following(user_one, user_two):
    return get_model('profile', 'Follow').objects.filter(user=user_one, user_follow=user_two, active=True).exists()

def get_key(name, recipient, sender, obj):
    recipient_pk = sender_pk = obj_pk = ''

    if recipient:
        recipient_pk = recipient.pk
    if sender:
        sender_pk = sender.pk
    if obj:
        obj_pk = obj.pk

    return '%s_%s_%s_%s' % (name, recipient_pk, sender_pk, obj_pk)

def is_duplicate(name, recipient, sender, obj):
    key = get_key(name, recipient, sender, obj)
    cache, created = get_model('profile', 'NotificationCache').objects.get_or_create(key=key)
    if created:
        return False

    return True

# TODO: should use display_name instead of first_name and last_name
def notify_by_mail(users, notification_name, sender, extra_context=None):
    """
    Sends an email to all users for the specified notification

    Variable users is a list of django auth user instances.
    """
    if extra_context is None:
        extra_context = {}

    if sender.is_hidden:
        return

    extra_context['domain'] = Site.objects.get_current().domain
    extra_context['sender_name'] = sender.display_name
    extra_context['sender_link'] = 'http://%s%s' % (extra_context['domain'], sender.get_absolute_url())
    extra_context['sender_updates_link'] = 'http://%s%s' % (extra_context['domain'], reverse('profile-likes', args=[sender.slug]))
    if 'object_link' in extra_context:
        extra_context['object_link'] = 'http://%s%s' % (extra_context['domain'], extra_context['object_link'])

    body_template_name = 'profile/notifications/email_%s.html' % (notification_name,)
    subject_template_name = 'profile/notifications/subject_%s.html' % (notification_name,)

    current_language = get_language()

    notification_count = 0

    for user in users:
        if user and user.email and user.is_active:
            if user.language:
                activate(user.language)
            else:
                activate(settings.LANGUAGE_CODE)

            extra_context['recipient_name'] = user.display_name

            subject = ''.join(render_to_string(subject_template_name, extra_context).splitlines())
            # XXX: undocumented feature in HTMLParser, look here if python is
            # upgraded
            subject = HTMLParser.HTMLParser().unescape(subject)
            html_body = render_to_string(body_template_name, extra_context)
            text_body = strip_tags(html_body)
            text_body = HTMLParser.HTMLParser().unescape(text_body)
            recipients = [user.email]

            msg = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, recipients)
            msg.attach_alternative(html_body, 'text/html')
            msg.send()

            notification_count = notification_count + 1

    stats, created = get_model('statistics', 'NotificationEmailStats').objects.get_or_create(notification_name=notification_name,
                                                                                             defaults={'notification_count': notification_count})
    if not created:
        stats.notification_count = stats.notification_count + notification_count
        stats.save()

    activate(current_language)

def notify_with_mandrill_template(users, notification_name, merge_vars):
    """
    New version of mail notifications using Mandrill templates (manually added to account beforehand) instead of local html templates

    Sends an email to all users for the specified notification
    Variable users is a list of django auth user instances.
    """
    emails = []
    usernames = {}
    notification_count = 0

    """ extract email addresses and usernames"""
    for user in users:
        if user and user.email and user.is_active:
            emails.append(user.email)
            usernames[user.email] = {'USERNAME': user.display_name}
            notification_count = notification_count + 1

    """ create message object """
    msg = EmailMessage(from_email=settings.DEFAULT_FROM_EMAIL, to=emails)

    #NOTICE: currently using the subject as defined in Mandrill template, thus also using merge tags there
    msg.template_name = notification_name           # A Mandrill template name

    # this is not currently used, but for some reason the API fails if this is not set.
    # it could say anything, none of this lands in the final email
    msg.template_content = {                        # Content blocks to fill in
        'EMPTY_BLOCK': "<a href='apprl.com/*|URL|*'>Hello there!</a>"
    }
    apprl_logo_url = retrieve_static_url("logo.png")

    msg.global_merge_vars = {                       # values to merge into template
        'LOGOURL': apprl_logo_url,
        'FBICONURL': retrieve_static_url("icon-facebook.png"),
        'TWITTERICONURL': retrieve_static_url("icon-twitter.png"),
        'PINTERESTICONURL': retrieve_static_url("icon-pinterest.png"),
        'INSTAICONURL': retrieve_static_url("icon-instagram.png")
    }

    msg.global_merge_vars.update(merge_vars) #add specific parameters
    #development only
    #msg.subaccount ="apprl_testing"

    msg.merge_vars = usernames    # Per-recipient merge tags, here adding personalized names
    msg.send()

    current_language = get_language()
    stats, created = get_model('statistics', 'NotificationEmailStats').objects.get_or_create(notification_name=notification_name,
                                                                                             defaults={'notification_count': notification_count})
    if not created:
        stats.notification_count = stats.notification_count + notification_count
        stats.save()

    activate(current_language)

def retrieve_full_url(path):
    """
        append current hostname to front of URL
    """
    domain = settings.STATIC_URL
    if domain[-1] == "/":
        if path[0] == "/":
            path = path.replace("/","",1)
    return '%s%s' % (domain, path)

def retrieve_static_url(path,domain=None):
    """
        append current hostname to front of URL for static email content
    """
    if not domain:
        domain = settings.STATIC_URL
    static_location = settings.APPAREL_EMAIL_IMAGE_ROOT
    if not domain.startswith("http"):
        domain = ""
        static_location = "/%s/" % static_location
    else:
        static_location = "%s/" % static_location
    return '%s%s%s' % (domain, static_location, path)

#
# COMMENT LOOK CREATED
#

@task(name='profile.notifications.process_comment_look_created', max_retries=5, ignore_result=True)
def process_comment_look_created(recipient, sender, comment, **kwargs):
    """
    Process notification for a comment made by sender on a look created by
    recipient.
    """
    logger = process_comment_look_created.get_logger(**kwargs)
    if is_duplicate('comment_look_created', recipient, sender, comment):
        return 'duplicate'

    if sender == recipient:
        return 'same user'

    notify_user = None
    if recipient.comment_look_created == 'A':
        notify_user = recipient
    elif recipient.comment_look_created == 'F':
        if is_following(recipient, sender):
            notify_user = recipient

    if notify_user and sender:
        notify_by_mail([notify_user], 'comment_look_created', sender, {
            'object_title': comment.content_object.title,
            'object_link': comment.content_object.get_absolute_url(),
            'comment': comment.comment
        })

        return get_key('comment_look_created', recipient, sender, comment)

    if not notify_user and sender:
        logger.error('No user to notify and no sender')
    elif not notify_user:
        logger.error('No user to notify')
    elif not sender:
        logger.error('No sender')

#
# COMMENT PRODUCT COMMENT
#

@task(name='profile.notifications.process_comment_product_comment', max_retries=5, ignore_result=True)
def process_comment_product_comment(recipient, sender, comment, **kwargs):
    """
    Process notification for a comment made by sender on a product already
    commented by X.
    """
    logger = process_comment_product_comment.get_logger(**kwargs)
    if is_duplicate('comment_product_comment', recipient, sender, comment):
        return 'duplicate'

    content_object = comment.content_object
    content_object_content_type = ContentType.objects.get_for_model(content_object)

    notify_users = set()
    comments = Comment.objects.filter(content_type=content_object_content_type, object_pk=content_object.pk).select_related('apparel_profile')
    for comment_obj in comments:
        if comment_obj.user != sender and comment_obj.user not in notify_users:
            notification_setting = getattr(comment_obj.user, 'comment_product_comment')
            if notification_setting == 'A':
                notify_users.add(comment_obj.user)
            elif notification_setting == 'F':
                if is_following(comment_obj.user, sender):
                    notify_users.add(comment_obj.user)

    title = u'%s %s' % (content_object.manufacturer, content_object.product_name)
    if notify_users and sender:
        notify_by_mail(list(notify_users), 'comment_product_comment', sender, {
            'object_title': title,
            'object_link': content_object.get_absolute_url(),
            'comment': comment.comment
        })

        return get_key('comment_product_comment', recipient, sender, comment)

    if not notify_users and sender:
        logger.error('No user to notify and no sender')
    elif not notify_users:
        logger.error('No user to notify')
    elif not sender:
        logger.error('No sender')

#
# COMMENT LOOK COMMENT
#

@task(name='profile.notifications.process_comment_look_comment', max_retries=5, ignore_result=True)
def process_comment_look_comment(recipient, sender, comment, **kwargs):
    """
    Process notification for a comment made by sender on a look already
    commented by X.
    """
    logger = process_comment_look_comment.get_logger(**kwargs)
    if is_duplicate('comment_look_comment', recipient, sender, comment):
        return 'duplicate'

    content_object = comment.content_object
    content_object_content_type = ContentType.objects.get_for_model(content_object)

    notify_users = set()
    comments = Comment.objects.filter(content_type=content_object_content_type, object_pk=content_object.pk).select_related('apparel_profile')
    for comment_obj in comments:
        if comment_obj.user != sender and comment_obj.user not in notify_users:
            notification_setting = getattr(comment_obj.user, 'comment_look_comment')
            if notification_setting == 'A':
                notify_users.add(comment_obj.user)
            elif notification_setting == 'F':
                if is_following(comment_obj.user, sender):
                    notify_users.add(comment_obj.user)

    title = content_object.title
    if notify_users and sender:
        notify_by_mail(list(notify_users), 'comment_look_comment', sender, {
            'object_title': title,
            'object_link': content_object.get_absolute_url(),
            'comment': comment.comment
        })

        return get_key('comment_look_comment', recipient, sender, comment)

    if not notify_users and sender:
        logger.error('No user to notify and no sender')
    elif not notify_users:
        logger.error('No user to notify')
    elif not sender:
        logger.error('No sender')

#
# COMMENT PRODUCT WARDROBE
#

@task(name='profile.notifications.process_comment_product_wardrobe', max_retries=5, ignore_result=True)
def process_comment_product_wardrobe(recipient, sender, comment, **kwargs):
    """
    Process notification for a comment made by sender on a product in
    user X wardrobe.
    """
    logger = process_comment_product_wardrobe.get_logger(**kwargs)
    if is_duplicate('comment_product_wardrobe', recipient, sender, comment):
        return 'duplicate'

    content_object = comment.content_object

    notify_users = set()
    for product_like in content_object.likes.iterator():
        if product_like.user != sender and product_like.user not in notify_users:
            if product_like.user.comment_product_wardrobe == 'A':
                notify_users.add(product_like.user)
            elif product_like.user.comment_product_wardrobe == 'F':
                if is_following(product_like.user, sender):
                    notify_users.add(product_like.user)

    if notify_users and sender:
        notify_by_mail(list(notify_users), 'comment_product_wardrobe', sender, {
            'object_title': u'%s %s' % (content_object.manufacturer, content_object.product_name),
            'object_link': content_object.get_absolute_url(),
            'comment': comment.comment
        })

        return get_key('comment_product_wardrobe', recipient, sender, comment)

    if not notify_users and sender:
        logger.error('No user to notify and no sender')
    elif not notify_users:
        logger.error('No user to notify')
    elif not sender:
        logger.error('No sender')

#
# LIKE LOOK CREATED
#
@task(name='profile.notifications.process_like_look_created', max_retries=5, ignore_result=True)
def process_like_look_created(recipient, sender, look_like, **kwargs):
    """
    Process notification for a like by sender on a look created by recipient.
    """
    if sender and sender.is_hidden:
        return
    logger = process_like_look_created.get_logger(**kwargs)
    if is_duplicate('like_look_created', recipient, sender, look_like):
        return 'duplicate'

    if sender == recipient:
        return 'sender is recipient, no notification'

    notify_user = None
    if recipient.comment_look_created == 'A':
        notify_user = recipient
    elif recipient.comment_look_created == 'F':
        if is_following(recipient, sender):
            notify_user = recipient

    if notify_user and sender:
        merge_vars = {}
        domain = Site.objects.get_current().domain
        sender_link = retrieve_full_url(sender.get_absolute_url())
        merge_vars['PROFILEURL'] = sender_link
        look_url_link = 'http://%s%s' % (domain, look_like.look.get_absolute_url())
        merge_vars['LOOKURL'] = look_url_link
        look_name = look_like.look.title
        merge_vars['LOOKNAME'] = look_name
        look_photo_url = look_like.look.static_image.url
        merge_vars['LOOKPHOTOURL'] = look_photo_url
        if sender.image:
            profile_photo_url = get_thumbnail(sender.avatar_circular_medium, '500').url
        elif sender.facebook_user_id:
            profile_photo_url = 'http://graph.facebook.com/%s/picture?width=208' % sender.facebook_user_id
        else:
            profile_photo_url = staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE)

        merge_vars['LIKERNAME'] = sender.display_name
        merge_vars['PROFILEPHOTOURL'] = profile_photo_url

        event, created = get_model('profile', 'NotificationEvent').objects.get_or_create(owner=notify_user,
                                                                                actor=sender,
                                                                                type="LIKELOOK",
                                                                                look=look_like.look)
        event.email_Sent = True
        event.save()
        notify_with_mandrill_template([notify_user], "likedLook", merge_vars)

        return get_key('like_look_created', recipient, sender, look_like)

    if not notify_user and sender:
        logger.error('No user to notify and no sender')
    elif not notify_user:
        logger.error('No user to notify')
    elif not sender:
        logger.error('No sender')

#
# FOLLOW USER
#

def get_avatar_url(user):
    """
    retrieve full url to a profile picture
    """
    if user.image:
        profile_photo_url =  retrieve_full_url(get_thumbnail(user.avatar_circular_medium, '500').url)
    elif user.facebook_user_id:
        profile_photo_url = 'http://graph.facebook.com/%s/picture?width=208' % user.facebook_user_id
    else:
        profile_photo_url = retrieve_full_url(staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE))
    return profile_photo_url

@task(name='profile.notifications.process_follow_user', max_retries=5, ignore_result=True)
def process_follow_user(recipient, sender, follow, **kwargs):
    """
    Process notification for sender following recipient.
    """

    if sender and sender.is_hidden:
        return
    logger = process_follow_user.get_logger(**kwargs)
    if is_duplicate('follow_user', recipient, sender, None):
        return 'duplicate'

    notify_user = None
    if recipient.follow_user == 'A':
        notify_user = recipient
        #if is_following(recipient, sender):
            #TODO handle in new templates

    if notify_user and sender:
        merge_vars = dict()
        sender_link = retrieve_full_url(sender.get_absolute_url())
        merge_vars['PROFILEURL'] = sender_link

        if sender.image:
            profile_photo_url = get_thumbnail(sender.avatar_circular_medium, '500').url
        elif sender.facebook_user_id:
            profile_photo_url = 'http://graph.facebook.com/%s/picture?width=208' % sender.facebook_user_id
        else:
            profile_photo_url = staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE)

        merge_vars['FOLLOWERNAME'] = sender.display_name
        merge_vars['PROFILEPHOTOURL'] = profile_photo_url

        event, created = get_model('profile', 'NotificationEvent').objects.get_or_create(owner=notify_user,
                                                                                actor=sender,
                                                                                type="FOLLOW")
        event.email_sent = True #we are sending the email right away
        event.save()
        notify_with_mandrill_template([notify_user], "newFollower", merge_vars)
        return get_key('follow_user', recipient, sender, None)

    if not notify_user and sender:
        logger.error('No user to notify and no sender')
    elif not notify_user:
        logger.error('No user to notify')
    elif not sender:
        logger.error('No sender')

#
# FACEBOOK FRIENDS
#

@task(name='profile.notifications.facebook_friends', max_retries=5, ignore_result=True)
def process_facebook_friends(sender, graph_token, **kwargs):
    """
    Process notification for sender joining Apprl. Notifications will be sent
    to all facebook friends currently on Apprl.
    """
    logger = process_facebook_friends.get_logger(**kwargs)
    graph = facebook.GraphAPI(graph_token)
    fids = [f['id'] for f in graph.get_connections('me', 'friends').get('data', [])]
    # TODO: facebook login move
    for recipient in get_user_model().objects.filter(username__in=fids):
        if is_duplicate('facebook_friends', recipient, sender, None):
            logger.info('duplicate %s' % (recipient,))
            continue

        if recipient.facebook_friends == 'A' and sender:
            merge_vars = dict()
            sender_link = retrieve_full_url(sender.get_absolute_url())
            merge_vars['PROFILEURL'] = sender_link
            if sender.image:
                profile_photo_url = get_thumbnail(sender.avatar_circular_medium, '500').url
            elif sender.facebook_user_id:
                profile_photo_url = 'http://graph.facebook.com/%s/picture?width=208' % sender.facebook_user_id
            else:
                profile_photo_url = staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE)

            merge_vars['FRIENDNAME'] = sender.display_name
            merge_vars['PROFILEPHOTOURL'] = profile_photo_url
            event, created = get_model('profile', 'NotificationEvent').objects.get_or_create(owner=recipient,
                                                                                    actor=sender,
                                                                                    type="FB")
            event.email_sent = True #we are sending the email right away
            event.save()

            notify_with_mandrill_template([recipient], "fbFriend", merge_vars)

#
# SALE ALERT
#

@task(name='profile.notifications.process_sale_alert', max_retries=5, ignore_result=True)
def process_sale_alert(sender, product, original_currency, original_price, discount_price, first, **kwargs):
    """
    Process a new sale alert.
    """
    # Todo: function documentation

    logger = process_sale_alert.get_logger(**kwargs)

    template_name = 'first_sale_alert' if first else 'second_sale_alert'
    for likes in product.likes.filter(user__discount_notification=True, active=True).select_related('user'):

        if likes.user:
            # If we already sent a notification for this product and user it
            # must mean that the price has increased and then decreased.
            further = False
            if is_duplicate('sale_alert', likes.user, sender, product):
                further = True

            # Use the exchange rate from the user language
            language = settings.LANGUAGE_CODE
            if likes.user.language:
                language = likes.user.language

            currency = settings.LANGUAGE_TO_CURRENCY.get(language, settings.APPAREL_BASE_CURRENCY)
            rate = currency_exchange(currency, original_currency)

            # Round prices to no digits after the decimal comma
            locale_original_price = (original_price * rate).quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP)
            locale_discount_price = (discount_price * rate).quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP)

            domain = Site.objects.get_current().domain
            merge_vars = dict()

            # create NotificationEvent
            event, created = get_model('profile', 'NotificationEvent').objects.get_or_create(owner=likes.user,
                                                                                type="SALE",
                                                                                product=product,
                                                                                sale_new_price = locale_discount_price,
                                                                                sale_old_price = locale_original_price,
                                                                                sale_currency = currency)
            #if the user does not want an email just save the event and move on, otherwise build the email
            if not likes.user.discount_notification:
                event.save()
                continue

            if product.product_image:
                product_photo_url = get_thumbnail(product.product_image, '500').url
            else:
                product_photo_url = staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE)

            merge_vars['PRODUCTPHOTOURL'] = product_photo_url
            merge_vars['BRANDNAME'] = product.manufacturer.name
            merge_vars['PRODUCTNAME'] = product.product_name
            merge_vars['PRODUCTLINK'] = "http://%s%s" % (domain,product.get_absolute_url())
            merge_vars['BUYLINK'] = "http://%sredirect/%s/Product/0/" % (domain, product.pk)
            merge_vars['OLDPRICE'] = locale_original_price
            merge_vars['NEWPRICE'] = locale_discount_price
            merge_vars['CURRENCY'] = currency
            if further:
                merge_vars['FURTHER'] = further


            event.email_sent = True #we are sending the email right away
            event.save()
            notify_with_mandrill_template([likes.user], "itemSale", merge_vars)

def get_ref_time(days, monday=False):
    if days == 1:
        return timezone.now() - timedelta(days=1)
    else:
        ref_time = timezone.now() - timedelta(days=days)
        if monday:
            ref_time = ref_time - timedelta(days=(ref_time.isocalendar()[2] - 1))
        return ref_time

def calculate_period(period='D'):
    if period == 'D':
        # it is a daily summary
        period_name = 'daily'
        ref_time = get_ref_time(1)
    elif period == 'W':
        # it is a weekly summary
        period_name = 'weekly'
        ref_time = get_ref_time(7, True)
    elif period == 'M':
        # it is a weekly summary
        period_name = 'monthly'
        ref_time = get_ref_time(30, True)
    return period_name, ref_time

def send_activity_summaries(period):
    users_to_notify = get_model('profile', 'User').objects.filter(summary_mails=period)
    for user in users_to_notify:
        create_individual_summary(user, period)

#@periodic_task(name='apparel.notifications.user_activity_daily', run_every=crontab(minute='0', hour='15'))
def send_activity_daily_summaries():
    send_activity_summaries("D")

#@periodic_task(name='apparel.notifications.user_activity_weekly', run_every=crontab(minute='0', hour='15',day_of_week='saturday'))
def send_activity_weekly_summaries():
    send_activity_summaries("W")

def create_individual_summary(user, period):
    period_name, ref_time = calculate_period(period)
    events = get_model('profile', 'NotificationEvent').objects.filter(owner=user, created__gte=ref_time)
    latest_likes = get_model('apparel', 'ProductLike').objects.filter(user=user, created__gte=ref_time)

    look_likes = []
    new_followers = []
    sales = []

    merge_vars = dict()
    merge_vars['looklikes'] = []
    merge_vars['sales'] = []
    merge_vars['follows'] = []
    for event in events:
        if event.type == "LIKELOOK":
            details = {
                'name': event.look.title,
                'imgurl': retrieve_full_url(event.look.static_image.url),
                'url': retrieve_full_url(event.look.get_absolute_url()),
            }
            merge_vars['looklikes'].append(details)
            look_likes.append(event)
        elif event.type == "SALE":
            details = {
                'name': event.product.product_name,
                'imgurl': retrieve_full_url(get_thumbnail(event.product.product_image, '500').url),
                'url': retrieve_full_url(event.product.get_absolute_url()),
            }
            merge_vars['sales'].append(details)
            sales.append(event)
        elif event.type == "FOLLOW":
            details = {
                'name': event.actor.display_name,
                'imgurl': get_avatar_url(event.actor),
                'url': retrieve_full_url(event.actor.get_absolute_url()),
            }
            merge_vars['follows'].append(details)
            new_followers.append(event)

    merge_vars['products'] = []
    for productlike in latest_likes:
        product = productlike.product
        details = {
            'name': product.product_name,
            'imgurl': retrieve_full_url(get_thumbnail(product.product_image, '500').url),
            'url': retrieve_full_url(product.get_absolute_url()),
        }
        merge_vars['products'].append(details)

    merge_vars['PERIOD'] = period_name
    merge_vars['PROFILEURL'] = retrieve_full_url(user.get_absolute_url())

    notify_with_mandrill_template([user], "SummaryMail", merge_vars)

def create_look_like_summary(period):
    period_name, interesting_time = calculate_period(period)
    #include looks that users liked within the month for notifying them too
    ref_time = calculate_period('M')[1]
    look_likes = get_model('apparel', 'LookLike').objects.filter(created__gte=ref_time)

    like_dict = {}
    users_to_notify = {}
    #iterate through look likes
    for like in look_likes:
        look = like.look
        if(like.created > interesting_time):
            if look in like_dict:
                like_dict[look].append(like.user)
            else:
                like_dict[look] = [like.user]
        if like.user in users_to_notify:
            users_to_notify[like.user].append(look)
        else:
            users_to_notify[like.user] = [look]

    return like_dict, users_to_notify

def create_product_like_summary(period):
    period_name, interesting_time = calculate_period(period)
    #include products that users liked within the month for notifying them too
    ref_time = calculate_period('M')[1]
    product_likes = get_model('apparel', 'ProductLike').objects.filter(created__gte=ref_time)

    like_dict = {}
    users_to_notify = {}
    #iterate through look likes
    for like in product_likes:
        product = like.product
        if(like.created > interesting_time):
            if product in like_dict:
                like_dict[product].append(like.user)
            else:
                like_dict[product] = [like.user]
        if like.user in users_to_notify:
            users_to_notify[like.user].append(product)
        else:
            users_to_notify[like.user] = [product]

    return like_dict, users_to_notify


#@periodic_task(name='apparel.notifications.look_like_daily', run_every=crontab(minute='0', hour='20',))
def send_look_like_daily_summaries():
    send_look_like_summaries(period="D")

#@periodic_task(name='apparel.notifications.look_like_weekly', run_every=crontab(minute='0', hour='15',day_of_week='wednesday'))
def send_look_like_weekly_summaries():
    send_look_like_summaries(period="W")

def send_look_like_summaries(period="D"):
    look_likes, users_to_notify = create_look_like_summary(period)
    domain = Site.objects.get_current().domain
    #iterate over all users that created any likes within the given period
    for user in users_to_notify:
        #make sure the user wants this summary
        if user.look_like_summaries != period:
            continue
        looks = []
        merge_vars = {}
        if(period == 'D'):
            merge_vars['PERIOD'] = "today"
        elif(period == 'W'):
            merge_vars['PERIOD'] = "this week"

        for look in users_to_notify[user]:
            look_url_link = 'http://%s%s' % (domain, look.get_absolute_url())
            look_detail = { "LOOKURL" : look_url_link,
                            "LOOKNAME" : look.title,
                            "LOOKPHOTOURL" : look.static_image.url,
            }
            likers = []
            if(not look in look_likes):
                continue
            for liker in look_likes[look]:
                if not(liker == user and len(likers) <= 20):
                    if liker.image:
                        profile_photo_url = get_thumbnail(liker.avatar_circular_medium, '100').url
                    elif liker.facebook_user_id:
                        profile_photo_url = 'http://graph.facebook.com/%s/picture?width=208' % liker.facebook_user_id
                    else:
                        profile_photo_url = staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE)
                    sender_link = retrieve_full_url(liker.get_absolute_url())
                    likers.append({"USERNAME" : liker.display_name,
                                   "PROFILEURL" : sender_link,
                                   "PROFILEPICTUREURL" : profile_photo_url,
                    })
            if(len(likers) == 1):
                look_detail["SINGULAR"] = True
            elif(len(likers) == 2):
                look_detail["TWOLIKERS"] = True
                look_detail["SINGULAR"] = False
                look_detail["OTHERLIKERNAME"] = likers[1]["USERNAME"]
                look_detail["OTHERLIKERURL"] = likers[1]["PROFILEURL"]
            else:
                look_detail["TWOLIKERS"] = False
                look_detail["SINGULAR"] = False
                look_detail["NOOFLIKES"] = len(likers)-1
            look_detail["LIKERS"] = likers
            if likers:
                look_detail["ONELIKERNAME"] = likers[0]["USERNAME"]
                look_detail["ONELIKERURL"] = likers[0]["PROFILEURL"]
                looks.append(look_detail)

        merge_vars['LOOKS'] = looks
        notify_with_mandrill_template([user], "lookLikeSummary", merge_vars)

    return

#@periodic_task(name='apparel.notifications.product_like_daily', run_every=crontab(minute='0', hour='20',))
def send_product_like_daily_summaries():
    send_product_like_summaries("D")

#@periodic_task(name='apparel.notifications.product_like_weekly', run_every=crontab(minute='0', hour='15',day_of_week='monday'))
def send_product_like_weekly_summaries():
    send_product_like_summaries("W")

def send_product_like_summaries(period="D"):
    product_likes, users_to_notify = create_product_like_summary(period)
    domain = Site.objects.get_current().domain
    #iterate over all users that created any likes within the given period
    for user in users_to_notify:
        #make sure the user wants this summary
        if user.product_like_summaries != period:
            continue
        products = []
        merge_vars = {}
        if(period == 'D'):
            merge_vars['PERIOD'] = "today"

        elif(period == 'W'):
            merge_vars['PERIOD'] = "this week"

        for product in users_to_notify[user]:
            product_url_link = 'http://%s%s' % (domain, product.get_absolute_url())
            product_detail = {  "PRODUCTURL" : product_url_link,
                                "BRANDNAME" : product.manufacturer.name,
                                "PRODUCTNAME" : product.product_name,
                                "PRODUCTPHOTOURL" : get_thumbnail(product.product_image, '500').url,
            }
            likers = []
            if(not product in product_likes):
                continue
            for liker in product_likes[product]:
                if not(liker == user and len(likers) <= 20):
                    if liker.image:
                        profile_photo_url = get_thumbnail(liker.avatar_circular_medium, '100').url
                    elif liker.facebook_user_id:
                        profile_photo_url = 'http://graph.facebook.com/%s/picture?width=208' % liker.facebook_user_id
                    else:
                        profile_photo_url = staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE)
                    sender_link = retrieve_full_url(liker.get_absolute_url())
                    likers.append({"USERNAME" : liker.display_name,
                                   "PROFILEURL" : sender_link,
                                   "PROFILEPICTUREURL" : profile_photo_url,
                    })
            if(len(likers) == 1):
                product_detail["SINGULAR"] = True
            elif(len(likers) == 2):
                product_detail["TWOLIKERS"] = True
                product_detail["SINGULAR"] = False
                product_detail["OTHERLIKERNAME"] = likers[1]["USERNAME"]
                product_detail["OTHERLIKERURL"] = likers[1]["PROFILEURL"]
            else:
                product_detail["TWOLIKERS"] = False
                product_detail["SINGULAR"] = False
                product_detail["NOOFLIKES"] = len(likers)-1
            product_detail["LIKERS"] = likers
            if likers:
                product_detail["ONELIKERNAME"] = likers[0]["USERNAME"]
                product_detail["ONELIKERURL"] = likers[0]["PROFILEURL"]
                products.append(product_detail)

        merge_vars['PRODUCTS'] = products
        notify_with_mandrill_template([user], "productLikeSummary", merge_vars)

    return

#@periodic_task(name='apparel.notifications.earnings_daily', run_every=crontab(minute='0', hour='7',))
def send_earning_daily_summary():
    send_earning_summaries("D")

#@periodic_task(name='apparel.notifications.earnings_weekly', run_every=crontab(minute='0', hour='7',day_of_week='friday'))
def send_earning_weekly_summary():
    send_earning_summaries("W")

def get_vendor_logo(vendor):
    if(vendor.logotype):
        return get_thumbnail(vendor.logotype, '500').url
    else:
        return staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE)


def create_earning_summary(period):
    period_name, interesting_time = calculate_period(period)
    #include products that users liked within the month for notifying them too
    period_name, ref_time = calculate_period(period)
    PENDING = 2 #This can't be imported here but is originally 'Pending' fro STATUS_CHOICES in dashboard.models.Sale
    #fetch all earnings in the given period that are either sales or clicks
    earnings = get_model('dashboard', 'UserEarning').objects\
            .filter(Q(user_earning_type='publisher_sale_commission') | Q(user_earning_type='publisher_sale_click_commission')\
            , date__range=(ref_time, timezone.now()), status__gte=PENDING)\
            .order_by('-date')

    earning_dict = {}
    users_to_notify = {}
    #iterate through look likes
    for earning in earnings:
        user = earning.user
        earning_detail = {}
        if user in users_to_notify:
            #there are already earning for this user
            new_amount = earning.amount
            earning_detail['SUM'] = new_amount
            users_to_notify[user]["totalearning"] += new_amount
            earning_detail['VENDORNAME'] = earning.sale.vendor.name
            if(earning.user_earning_type == 'publisher_sale_commission'):
                product = earning.from_product
                earning_detail['PRODUCTSALE'] = True
                if not product:
                    #there is no associated product
                    vendor = earning.sale.vendor
                    if(vendor in users_to_notify[user]["othersales"]):
                        old_details = users_to_notify[user]["othersales"][vendor]
                        old_details['AMOUNT'] += 1
                        old_details['SUM'] += new_amount
                    else:
                        earning_detail['AMOUNT'] = 1
                        earning_detail['PHOTOURL'] = get_vendor_logo(vendor)
                        earning_detail['NOPRODUCT'] = True
                        users_to_notify[user]["othersales"][vendor] = earning_detail
                elif(product in users_to_notify[user]["productsales"]):
                    #aggregate earnings for same product
                    old_details = users_to_notify[user]["productsales"][product]
                    old_details['AMOUNT'] += 1
                    old_details['SUM'] += new_amount
                else:
                    #or create new one if it does not exist
                    earning_detail['AMOUNT'] = 1
                    earning_detail['BRANDNAME'] = product.manufacturer.name
                    earning_detail['PRODUCTNAME'] = product.product_name
                    earning_detail['PHOTOURL'] = get_thumbnail(product.product_image, '500').url
                    earning_detail['NOPRODUCT'] = False
                    users_to_notify[user]["productsales"][product] = earning_detail
            elif(earning.user_earning_type == 'publisher_sale_click_commission'):
                vendor = earning.sale.vendor
                earning_detail['PRODUCTSALE'] = False
                if(vendor in users_to_notify[user]["clickearnings"]):
                    #aggregate earnings for same vendor
                    old_details = users_to_notify[user]["clickearnings"][vendor]
                    old_details['SUM'] += new_amount
                else:
                    #or create new one if it does not exist
                    earning_detail['PHOTOURL'] = get_vendor_logo(vendor)
                    users_to_notify[user]["clickearnings"][vendor] = earning_detail
        else:
            #this is the first sale encoutered for the user
            #so create dicts for earnings
            product_sales = {}
            click_earnings = {}
            other_sales = {}
            earning_detail['SUM'] = earning.amount
            total_earnings = earning.amount
            earning_detail['VENDORNAME'] = earning.sale.vendor.name
            if(earning.user_earning_type == 'publisher_sale_commission'):
                earning_detail['PRODUCTSALE'] = True
                earning_detail['AMOUNT'] = 1
                product = earning.from_product
                if product:
                    earning_detail['BRANDNAME'] = product.manufacturer.name
                    earning_detail['PRODUCTNAME'] = product.product_name
                    earning_detail['PHOTOURL'] = get_thumbnail(product.product_image, '500').url
                    earning_detail['NOPRODUCT'] = False
                    product_sales[product] = earning_detail
                else:
                    earning_detail['NOPRODUCT'] = True
                    vendor = earning.sale.vendor
                    earning_detail['PHOTOURL'] = get_vendor_logo(vendor)
                    other_sales[vendor] = earning_detail
            elif(earning.user_earning_type == 'publisher_sale_click_commission'):
                earning_detail['PRODUCTSALE'] = False
                earning_detail['PHOTOURL'] = get_vendor_logo(earning.sale.vendor)
                click_earnings[earning.sale.vendor] = earning_detail
            users_to_notify[user] = {"productsales" : product_sales,
                                     "clickearnings" : click_earnings,
                                     "othersales" : other_sales,
                                     "totalearning" : total_earnings,
            }

    return earning_dict, users_to_notify, period_name


def send_earning_summaries(period):
    earnings, users_to_notify, period_name = create_earning_summary(period)
    domain = Site.objects.get_current().domain
    #iterate over all publishers and generate their summaries
    for user in users_to_notify:
        if user.earning_summaries != period:
            continue
        all_earnings = users_to_notify[user]["productsales"].values()
        all_earnings.extend(users_to_notify[user]["othersales"].values())
        all_earnings.extend(users_to_notify[user]["clickearnings"].values())
        sorted_earnings = sorted(all_earnings, key=lambda k: k['SUM'])
        for earning in sorted_earnings:
            earning["SUM"] = str(earning["SUM"])

        total_earning = users_to_notify[user]["totalearning"]
        merge_vars = {}
        merge_vars['PERIOD'] = period_name
        merge_vars['TOTAL'] = str(total_earning)
        merge_vars['EARNINGDETAILS'] = sorted_earnings

        notify_with_mandrill_template([user], "earningSummary", merge_vars)

    return
# def create_activity_summary(user, period):
#     activity = ActivityFeedRender(None, 'A', user).run()
