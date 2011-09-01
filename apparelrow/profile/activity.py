import logging

from django.db.models.signals import post_save, post_delete
from django.contrib.comments import signals as comments_signals
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from actstream.models import Follow

from apparel.models import LookLike, Look, Product
from apparel import signals as apparel_signals
from profile.notifications import process_like_look_created
from profile.notifications import process_comment_look_created
from profile.notifications import process_comment_look_comment
from profile.notifications import process_comment_product_wardrobe
from profile.notifications import process_comment_product_comment
from profile.notifications import process_follow_user

#
# Look like activity handlers
#

def like_look_handler(sender, **kwargs):
    instance = kwargs['instance']
    request = kwargs['request']
    if not instance.active or not hasattr(instance, 'user') or not hasattr(request, 'user'):
        return None

    process_like_look_created.delay(instance.look.user, request.user, instance)

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
        process_comment_look_created.delay(instance.content_object.user, request.user, instance)
        process_comment_look_comment.delay(instance.content_object.user, request.user, instance)

    product_content_type = ContentType.objects.get_for_model(Product)
    if instance.content_type == product_content_type:
        process_comment_product_comment.delay(None, request.user, instance)
        process_comment_product_wardrobe.delay(None, request.user, instance)

comments_signals.comment_was_posted.connect(comments_handler)

#
# Follow handler
#

def follow_handler(sender, **kwargs):
    instance = kwargs['instance']
    if not hasattr(instance, 'user') and instance.content_type == ContentType.objects.get_for_model(instance.user):
        return

    try:
        recipient = User.objects.get(pk=instance.object_id)
        process_follow_user.delay(recipient, instance.user, instance)
    except User.DoesNotExist:
        pass

    apparel_profile = recipient.get_profile()
    apparel_profile.followers_count = apparel_profile.followers_count + 1
    apparel_profile.save()

post_save.connect(follow_handler, sender=Follow)

def delete_follow_handler(sender, **kwargs):
    instance = kwargs['instance']
    try:
        user = User.objects.get(id=instance.object_id)
    except User.DoesNotExist:
        pass

    apparel_profile = user.get_profile()
    apparel_profile.followers_count = apparel_profile.followers_count - 1
    apparel_profile.save()

post_delete.connect(delete_follow_handler, sender=Follow)
