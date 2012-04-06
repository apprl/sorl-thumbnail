import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.cache import cache
from django.contrib.contenttypes.models import ContentType
from django.contrib.comments.models import Comment
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import get_language, activate
from actstream.models import Follow
from celery.task import task

from profile.models import NotificationCache

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
    cache, created = NotificationCache.objects.get_or_create(key=key)
    if created:
        return False

    return True

def notify_by_mail(users, notification_name, sender, extra_context=None):
    """
    Sends an email to all users for the specified notification
    """
    if extra_context is None:
        extra_context = {}

    extra_context['domain'] = Site.objects.get_current().domain
    extra_context['sender_first_name'] = sender.first_name
    extra_context['sender_last_name'] = sender.last_name
    extra_context['sender_link'] = 'http://%s%s' % (extra_context['domain'], sender.get_profile().get_absolute_url())
    if 'object_link' in extra_context:
        extra_context['object_link'] = 'http://%s%s' % (extra_context['domain'], extra_context['object_link'])

    body_template_name = 'profile/notifications/email_%s.html' % (notification_name,)
    subject_template_name = 'profile/notifications/subject_%s.html' % (notification_name,)

    current_language = get_language()

    for user in users:
        if user and user.email and user.is_active:
            if hasattr(user, 'get_profile'):
                activate(user.get_profile().language)
            else:
                activate(settings.LANGUAGE_CODE)

            extra_context['recipient_first_name'] = user.first_name
            extra_context['recipient_last_name'] = user.last_name

            subject = ''.join(render_to_string(subject_template_name, extra_context).splitlines())
            html_body = render_to_string(body_template_name, extra_context)
            text_body = strip_tags(html_body)
            recipients = [user.email]

            msg = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, recipients)
            msg.attach_alternative(html_body, 'text/html')
            msg.send()

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

    sender_content_type = ContentType.objects.get_for_model(sender)

    if sender == recipient:
        return 'same user'

    notify_user = None
    if recipient.get_profile().comment_look_created == 'A':
        notify_user = recipient
    elif recipient.get_profile().comment_look_created == 'F':
        if Follow.objects.filter(user=recipient, content_type=sender_content_type, object_id=sender.pk):
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

    sender_content_type = ContentType.objects.get_for_model(sender)
    content_object = comment.content_object
    content_object_content_type = ContentType.objects.get_for_model(content_object)

    notify_users = set()
    comments = Comment.objects.filter(content_type=content_object_content_type, object_pk=content_object.pk).select_related('apparel_profile')
    for comment_obj in comments:
        if comment_obj.user != sender and comment_obj.user not in notify_users:
            notification_setting = getattr(comment_obj.user.get_profile(), 'comment_product_comment')
            if notification_setting == 'A':
                notify_users.add(comment_obj.user)
            elif notification_setting == 'F':
                if Follow.objects.filter(user=comment_obj.user, content_type=sender_content_type, object_id=sender.pk):
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

    sender_content_type = ContentType.objects.get_for_model(sender)
    content_object = comment.content_object
    content_object_content_type = ContentType.objects.get_for_model(content_object)

    notify_users = set()
    comments = Comment.objects.filter(content_type=content_object_content_type, object_pk=content_object.pk).select_related('apparel_profile')
    for comment_obj in comments:
        if comment_obj.user != sender and comment_obj.user not in notify_users:
            notification_setting = getattr(comment_obj.user.get_profile(), 'comment_look_comment')
            if notification_setting == 'A':
                notify_users.add(comment_obj.user)
            elif notification_setting == 'F':
                if Follow.objects.filter(user=comment_obj.user, content_type=sender_content_type, object_id=sender.pk):
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

    sender_content_type = ContentType.objects.get_for_model(sender)
    content_object = comment.content_object

    notify_users = set()
    for product_like in content_object.likes.iterator():
        if product_like.user != sender and product_like.user not in notify_users:
            if product_like.user.get_profile().comment_product_wardrobe == 'A':
                notify_users.add(product_like.user)
            elif product_like.user.get_profile().comment_product_wardrobe == 'F':
                if Follow.objects.filter(user=product_like.user, content_type=sender_content_type, object_id=sender.pk):
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

    sender_content_type = ContentType.objects.get_for_model(sender)

    notify_user = None
    if recipient.get_profile().comment_look_created == 'A':
        notify_user = recipient
    elif recipient.get_profile().comment_look_created == 'F':
        if Follow.objects.filter(user=recipient, content_type=sender_content_type, object_id=sender.pk):
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

    recipient_content_type = ContentType.objects.get_for_model(recipient)
    sender_content_type = ContentType.objects.get_for_model(sender)

    notify_user = None
    template_name = 'follow_user'
    if recipient.get_profile().follow_user == 'A':
        notify_user = recipient
        if Follow.objects.filter(user=recipient, content_type=sender_content_type, object_id=sender.pk):
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
