import logging
import decimal
import HTMLParser
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
from django.core.files.storage import DefaultStorage

from sorl.thumbnail import get_thumbnail
from django.templatetags.static import static


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

def notifiy_with_mandrill_teplate(users, notification_name, notification_subject, sender, merge_vars, extra_context=None):

    """
    New version of mail notifications using Mandrill templates (manually added to account beforehand) instead of local html templates

    Sends an email to all users for the specified notification
    Variable users is a list of django auth user instances.
    """
    if extra_context is None:
        extra_context = {}
    if sender.is_hidden:
        return
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
    msg = EmailMessage(from_email="no-reply@example.com", to=emails)
    #NOTICE: currently using the subject as defined in Mandrill template, thus also using merge tags there
    msg.template_name = notification_name           # A Mandrill template name
    #this is not currently used, but for some reason the API fails if this is not set.
    #  it could say anything, none of this lands in the final email
    msg.template_content = {                        # Content blocks to fill in
        'EMPTY_BLOCK': "<a href='apprl.com/*|URL|*'>Hello there!</a>"
    }
    apprl_logo_url = "http://s-staging.apprl.com/static/email/logo.png" #TODO switch to deploy

    msg.global_merge_vars = {                       # values to merge into template
        'LOGOURL': apprl_logo_url,
        'FBICONURL': "http://s-staging.apprl.com/static/email/icon-facebook.png",
        'TWITTERICONURL': "http://s-staging.apprl.com/static/email/icon-twitter.png",
        'PINTERESTICONURL': "http://s-staging.apprl.com/static/email/icon-pinterest.png",
        'INSTAICONURL': "http://s-staging.apprl.com/static/email/icon-instagram.png"
    }
    msg.global_merge_vars.update(merge_vars) #add specific parameters

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
    """ append current hostname to front of URL
    """
    return settings.STATIC_URL + path


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
        merge_vars = dict()
        domain = Site.objects.get_current().domain
        sender_link = 'http://%s%s' % (domain, sender.get_absolute_url())
        merge_vars['PROFILEURL'] = sender_link
        look_url = look_like.look.get_absolute_url()
        merge_vars['LOOKURL'] = retrieve_full_url(look_url)
        look_name = look_like.look.title
        merge_vars['LOOKNAME'] = look_name
        look_photo_url = look_like.look.static_image.url
        merge_vars['LOOKPHOTOURL'] = retrieve_full_url(look_photo_url)

        if sender.image:
            profile_photo_url =  get_thumbnail(sender.image, '500').url
        elif sender.facebook_user_id:
            profile_photo_url = 'http://graph.facebook.com/%s/picture?width=208' % sender.facebook_user_id
        else:
            profile_photo_url = staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE)
        merge_vars['LIKERNAME'] = sender.display_name
        merge_vars['PROFILEPHOTOURL'] = retrieve_full_url(profile_photo_url)
        # create NotificationEvent
        event = get_model('profile', 'NotificationEvent').objects.get_or_create(owner=notify_user,
                                                                                actor=sender,
                                                                                type="LIKELOOK",
                                                                                look=look_like.look,
                                                                                email_sent=True)
        event.save()
     #   notifiy_with_mandrill_teplate([notify_user], "likedLook", "", sender, merge_vars)

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
    if recipient.follow_user == 'A':
        notify_user = recipient
        #if is_following(recipient, sender):
            #TODO handle in new templates

    if notify_user and sender:
        merge_vars = dict()
        domain = Site.objects.get_current().domain
        sender_link = 'http://%s%s' % (domain, sender.get_absolute_url())
        merge_vars['PROFILEURL'] = sender_link
        if sender.image:
            profile_photo_url =  get_thumbnail(sender.image, '500').url
        elif sender.facebook_user_id:
            profile_photo_url = 'http://graph.facebook.com/%s/picture?width=208' % sender.facebook_user_id
        else:
            profile_photo_url = staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE)
        merge_vars['FOLLOWERNAME'] = sender.display_name
        merge_vars['PROFILEPHOTOURL'] = retrieve_full_url(profile_photo_url)
        event = get_model('profile', 'NotificationEvent').objects.get_or_create(owner=notify_user,
                                                                                actor=sender,
                                                                                type="FOLLOW",
                                                                                email_sent=True)
        event.email_sent = True #we are sending the email right away
        event.save()
        notifiy_with_mandrill_teplate([notify_user], "newFollower", "You have a new follower on Apprl!", sender, merge_vars)
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
            domain = Site.objects.get_current().domain
            sender_link = 'http://%s%s' % (domain, sender.get_absolute_url())
            merge_vars['PROFILEURL'] = sender_link
            if sender.image:
                profile_photo_url =  get_thumbnail(sender.image, '500').url
            elif sender.facebook_user_id:
                profile_photo_url = 'http://graph.facebook.com/%s/picture?width=208' % sender.facebook_user_id
            else:
                profile_photo_url = staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE)
            merge_vars['FRIENDNAME'] = sender.display_name
            merge_vars['PROFILEPHOTOURL'] = retrieve_full_url(profile_photo_url)
            # create NotificationEvent
            event = get_model('profile', 'NotificationEvent').objects.get_or_create(owner=recipient,
                                                                                    actor=sender,
                                                                                    type="FB",
                                                                                email_sent=True)
            event.email_sent = True #we are sending the email right away
            event.save()
            notifiy_with_mandrill_teplate([recipient], "fbFriend", "new FB friend on Apprl", sender, merge_vars)

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
           # if is_duplicate('sale_alert', likes.user, sender, product):
                #TODO adapt this for new templates

            # Use the exchange rate from the user language
            language = settings.LANGUAGE_CODE
            if likes.user.language:
                language = likes.user.language

            currency = settings.LANGUAGE_TO_CURRENCY.get(language, settings.APPAREL_BASE_CURRENCY)
            rate = currency_exchange(currency, original_currency)

            # Round prices to no digits after the decimal comma
            locale_original_price = (original_price * rate).quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP)
            locale_discount_price = (discount_price * rate).quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP)

            merge_vars = dict()
            if product.image:
                product_photo_url = get_thumbnail(product.image, '500').url
            else:
                product_photo_url = staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE)
            merge_vars['PRODUCTPHOTOURL'] = retrieve_full_url(product_photo_url)
            merge_vars['PRODUCTNAME'] = product.product_name
            merge_vars['PRODUCTLINK'] = retrieve_full_url(product.get_absolute_url())
            merge_vars['OLDPRICE'] = locale_original_price
            merge_vars['NEWPRICE'] = locale_discount_price
            merge_vars['CURRENCY'] = currency

            # create NotificationEvent
            event = get_model('profile', 'NotificationEvent').objects.get_or_create(owner=likes.use,
                                                                                type="SALE",
                                                                                product=product,
                                                                                email_sent=True,
                                                                                sale_new_price = locale_discount_price,
                                                                                sale_old_price = locale_original_price,
                                                                                sale_currency = currency)

            event.email_sent = True #we are sending the email right away
            event.save()
            notifiy_with_mandrill_teplate([likes.user], "itemSale", "A product you like has dropped in price!", sender, merge_vars)