import logging

from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.comments.signals import comment_was_posted
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from apparelrow.activity_feed.models import Activity

from apparelrow.profile.models import Follow

from apparelrow.profile.notifications import process_comment_look_created
from apparelrow.profile.notifications import process_comment_look_comment
from apparelrow.profile.notifications import process_comment_product_wardrobe
from apparelrow.profile.notifications import process_comment_product_comment


#
# Comment activity handler
#

@receiver(comment_was_posted, dispatch_uid='profile.activity.comments_handler')
def comments_handler(sender, **kwargs):
    instance = kwargs['comment']
    request = kwargs['request']
    if not hasattr(request, 'user'):
        return

    if instance.content_type is None:
        return

    if instance.content_type.model == 'look':
        process_comment_look_created.delay(instance.content_object.user, request.user, instance)
        process_comment_look_comment.delay(instance.content_object.user, request.user, instance)

    elif instance.content_type.model == 'product':
        process_comment_product_comment.delay(None, request.user, instance)
        process_comment_product_wardrobe.delay(None, request.user, instance)

