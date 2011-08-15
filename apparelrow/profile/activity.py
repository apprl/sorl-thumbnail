import logging

from django.db.models.signals import post_save
from django.contrib.comments import signals as comments_signals
from django.contrib.contenttypes.models import ContentType
from actstream.models import Follow

from apparel.models import LookLike, Look, Product
from apparel import signals as apparel_signals
from profile.messaging import send_notification

#
# Look like activity handlers
#

def like_look_handler(sender, **kwargs):
    instance = kwargs['instance']
    request = kwargs['request']
    if not instance.active or not hasattr(instance, 'user') or not hasattr(request, 'user'):
        return None

    send_notification('like_look_created',
                      instance.look.user.pk,
                      request.user.pk,
                      instance._meta.app_label,
                      instance._meta.module_name,
                      instance._get_pk_val())

apparel_signals.like.connect(like_look_handler, sender=LookLike)


#
# Comment activity handler
#

def comments_handler(sender, **kwargs):
    instance = kwargs['comment']
    request = kwargs['request']
    if not hasattr(request, 'user'):
        return

    if instance.content_type is None:
        return

    look_content_type = ContentType.objects.get_for_model(Look)
    if instance.content_type == look_content_type:
        send_notification('comment_look_created',
                          instance.content_object.user.pk,
                          request.user.pk,
                          instance._meta.app_label,
                          instance._meta.module_name,
                          instance._get_pk_val())
        send_notification('comment_look_comment',
                          instance.content_object.user.pk,
                          request.user.pk,
                          instance._meta.app_label,
                          instance._meta.module_name,
                          instance._get_pk_val())

    product_content_type = ContentType.objects.get_for_model(Product)
    if instance.content_type == product_content_type:
        send_notification('comment_product_comment',
                          None,
                          request.user.pk,
                          instance._meta.app_label,
                          instance._meta.module_name,
                          instance._get_pk_val())
        send_notification('comment_product_wardrobe',
                          None,
                          request.user.pk,
                          instance._meta.app_label,
                          instance._meta.module_name,
                          instance._get_pk_val())

comments_signals.comment_was_posted.connect(comments_handler)


#
# Follow handler
#

def follow_handler(sender, **kwargs):
    instance = kwargs['instance']
    if not hasattr(instance, 'user') and instance.content_type == ContentType.objects.get_for_model(instance.user):
        return

    send_notification('follow_user',
                      instance.object_id,
                      instance.user.pk,
                      instance._meta.app_label,
                      instance._meta.module_name,
                      instance._get_pk_val())

post_save.connect(follow_handler, sender=Follow)
