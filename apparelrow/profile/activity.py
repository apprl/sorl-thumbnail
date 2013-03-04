import logging

from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.comments.signals import comment_was_posted
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from activity_feed.models import Activity

from profile.models import Follow

from profile.notifications import process_comment_look_created
from profile.notifications import process_comment_look_comment
from profile.notifications import process_comment_product_wardrobe
from profile.notifications import process_comment_product_comment
from profile.notifications import process_follow_user


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

#
# Follow handlers
#

@receiver(post_save, sender=Follow, dispatch_uid='profile.activity.post_save_follow_handler')
def post_save_follow_handler(sender, instance, **kwargs):
    """
    Post save handler for follow objects. Updates followers count on user
    profile and attempts to notify users about this new follow object.
    """
    apparel_profile = instance.user_follow
    if instance.active:
        apparel_profile.followers_count = apparel_profile.followers_count + 1
        process_follow_user.delay(instance.user_follow, instance.user, instance)
        Activity.objects.push_activity(instance.user, 'follow', instance.user_follow, instance.user.gender)
    else:
        apparel_profile.followers_count = apparel_profile.followers_count - 1
        Activity.objects.pull_activity(instance.user, 'follow', instance.user_follow)
    apparel_profile.save()

@receiver(pre_delete, sender=Follow, dispatch_uid='profile.activity.pre_delete_follow_handler')
def pre_delete_follow_handler(sender, instance, **kwargs):
    """
    Pre delete handler for follow objects. Updates followers count on user
    profile.
    """
    apparel_profile = instance.user_follow
    apparel_profile.followers_count = apparel_profile.followers_count - 1
    apparel_profile.save()

    Activity.objects.pull_activity(instance.user, 'follow', instance.user_follow)
