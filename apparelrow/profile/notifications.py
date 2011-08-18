import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.contrib.contenttypes.models import ContentType
from django.contrib.comments.models import Comment
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import get_language, activate
from actstream.models import Follow

from apparel.models import Wardrobe

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
            activate(user.get_profile().language)

            extra_context['recipient_first_name'] = user.first_name
            extra_context['recipient_last_name'] = user.last_name

            subject = ''.join(render_to_string(subject_template_name, extra_context).splitlines())
            html_body = render_to_string(body_template_name, extra_context)
            text_body = strip_tags(html_body)
            recipients = [user.email]

            msg = EmailMultiAlternatives(subject, text_body, 'Apparelrow <no-reply@apparelrow.com>', recipients)
            msg.attach_alternative(html_body, 'text/html')
            msg.send()

    activate(current_language)

def process_comment_look_created(recipient, sender, comment):
    """
    Process notification for a comment made by sender on a look created by
    recipient.
    """
    sender_content_type = ContentType.objects.get_for_model(sender)

    notify_user = None
    if recipient.get_profile().comment_look_created == 'A':
        notify_users = recipient
    elif recipient.get_profile().comment_look_created == 'F':
        if Follow.objects.filter(user=recipient, content_type=sender_content_type, object_id=sender.pk):
            notify_user = recipient

    if notify_user:
        notify_by_mail([notify_user], 'comment_look_created', sender, {
            'object_title': comment.content_object.title,
            'object_link': comment.content_object.get_absolute_url(),
            'comment': comment.comment
        })

def comment_common(notification_name, recipient, sender, comment):
    """
    Process notification for a comment made by sender on any model already
    commented by X.
    """
    sender_content_type = ContentType.objects.get_for_model(sender)
    content_object = comment.content_object
    content_object_content_type = ContentType.objects.get_for_model(content_object)

    notify_users = set()
    comments = Comment.objects.filter(content_type=content_object_content_type, object_pk=content_object.pk).select_related('apparel_profile')
    for comment_obj in comments:
        if comment_obj.user != sender and comment_obj.user not in notify_users:
            notification_setting = getattr(comment_obj.user.get_profile(), notification_name)
            if notification_setting == 'A':
                notify_users.add(comment_obj.user)
            elif notification_setting == 'F':
                if Follow.objects.filter(user=comment_obj.user, content_type=sender_content_type, object_id=sender.pk):
                    notify_users.add(comment_obj.user)

    if notification_name == 'comment_product_comment':
        title = u'%s %s' % (content_object.manufacturer, content_object.product_name)
    elif notification_name == 'comment_look_comment':
        title = content_object.title

    if notify_users:
        notify_by_mail(list(notify_users), notification_name, sender, {
            'object_title': title,
            'object_link': content_object.get_absolute_url(),
            'comment': comment.comment
        })

def process_comment_product_comment(recipient, sender, comment):
    """
    Process notification for a comment made by sender on a product already
    commented by X.
    """
    comment_common('comment_product_comment', recipient, sender, comment)

def process_comment_look_comment(recipient, sender, comment):
    """
    Process notification for a comment made by sender on a look already
    commented by X.
    """
    comment_common('comment_look_comment', recipient, sender, comment)

def process_comment_product_wardrobe(recipient, sender, comment):
    """
    Process notification for a comment made by sender on a product in
    user X wardrobe.
    """
    sender_content_type = ContentType.objects.get_for_model(sender)
    content_object = comment.content_object

    notify_users = set()
    for wardrobe in Wardrobe.objects.filter(products=content_object).select_related('apparel_profile'):
        if wardrobe.user != sender and wardrobe.user not in notify_users:
            if wardrobe.user.get_profile().comment_product_wardrobe == 'A':
                notify_users.add(wardrobe.user)
            elif wardrobe.user.get_profile().comment_product_wardrobe == 'F':
                if Follow.objects.filter(user=wardrobe.user, content_type=sender_content_type, object_id=sender.pk):
                    notify_users.add(wardrobe.user)

    if notify_users:
        notify_by_mail(list(notify_users), 'comment_product_wardrobe', sender, {
            'object_title': u'%s %s' % (content_object.manufacturer, content_object.product_name),
            'object_link': content_object.get_absolute_url(),
            'comment': comment.comment
        })

def process_like_look_created(recipient, sender, look_like):
    """
    Process notification for a like by sender on a look created by recipient.
    """
    sender_content_type = ContentType.objects.get_for_model(sender)

    notify_user = None
    if recipient.get_profile().comment_look_created == 'A':
        notify_user = recipient
    elif recipient.get_profile().comment_look_created == 'F':
        if Follow.objects.filter(user=recipient, content_type=sender_content_type, object_id=sender.pk):
            notify_user = recipient

    if notify_user:
        notify_by_mail([notify_user], 'like_look_created', sender, {
            'object_title': look_like.look.title,
            'object_link': look_like.look.get_absolute_url()
        })

def process_follow_user(recipient, sender, follow):
    """
    Process notification for sender following recipient.
    """
    recipient_content_type = ContentType.objects.get_for_model(recipient)
    sender_content_type = ContentType.objects.get_for_model(sender)

    notify_user = None
    template_name = 'follow_user'
    if recipient.get_profile().follow_user == 'A':
        notify_user = recipient
        if Follow.objects.filter(user=recipient, content_type=sender_content_type, object_id=sender.pk):
            template_name = 'follow_user_following'
    elif recipient.get_profile().follow_user == 'F':
        if Follow.objects.filter(user=recipient, content_type=sender_content_type, object_id=sender.pk):
            notify_user = recipient
            template_name = 'follow_user_following'

    if notify_user:
        notify_by_mail([notify_user], template_name, sender)
