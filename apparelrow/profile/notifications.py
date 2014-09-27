import logging
import decimal
import HTMLParser

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
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

import facebook

from celery.task import task

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
        if is_following(user, sender):
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
        notify_by_mail([notify_user], 'like_look_created', sender, {
            'object_title': look_like.look.title,
            'object_link': look_like.look.get_absolute_url()
        })

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

@task(name='profile.notifications.process_follow_user', max_retries=5, ignore_result=True)
def process_follow_user(recipient, sender, follow, **kwargs):
    """
    Process notification for sender following recipient.
    """
    logger = process_follow_user.get_logger(**kwargs)
    if is_duplicate('follow_user', recipient, sender, None):
        return 'duplicate'

    notify_user = None
    template_name = 'follow_user'
    if recipient.follow_user == 'A':
        notify_user = recipient
        if is_following(recipient, sender):
            template_name = 'follow_user_following'

    if notify_user and sender:
        notify_by_mail([notify_user], template_name, sender)

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
            notify_by_mail([recipient], 'facebook_friends', sender)


#
# SALE ALERT
#

@task(name='profile.notifications.process_sale_alert', max_retries=5, ignore_result=True)
def process_sale_alert(sender, product, original_currency, original_price, discount_price, first, **kwargs):
    """
    Process a new sale alert.
    """
    logger = process_sale_alert.get_logger(**kwargs)

    template_name = 'first_sale_alert' if first else 'second_sale_alert'
    for likes in product.likes.filter(user__discount_notification=True, active=True).select_related('user'):
        if likes.user and likes.user.discount_notification:
            # If we already sent a notification for this product and user it
            # must mean that the price has increased and then decreased.
            if is_duplicate('sale_alert', likes.user, sender, product):
                template_name = 'second_sale_alert'

            # Use the exchange rate from the user language
            language = settings.LANGUAGE_CODE
            if likes.user.language:
                language = likes.user.language

            currency = settings.LANGUAGE_TO_CURRENCY.get(language, settings.APPAREL_BASE_CURRENCY)
            rate = currency_exchange(currency, original_currency)

            # Round prices to no digits after the decimal comma
            locale_original_price = (original_price * rate).quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP)
            locale_discount_price = (discount_price * rate).quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP)

            notify_by_mail([likes.user], template_name, sender, {
                'brand_name': sender.display_name,
                'product_name': product.product_name,
                'object_link': product.get_absolute_url(),
                'original_price': '%s %s' % (number_format(locale_original_price, use_l10n=False, force_grouping=True), currency),
                'discount_price': '%s %s' % (number_format(locale_discount_price, use_l10n=False, force_grouping=True), currency),
            })
