import logging

from django.db.models.signals import post_save, pre_delete, post_delete
from django.contrib.comments import signals as comments_signals
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from actstream.models import Follow, Action

from profile.notifications import process_comment_look_created
from profile.notifications import process_comment_look_comment
from profile.notifications import process_comment_product_wardrobe
from profile.notifications import process_comment_product_comment
from profile.notifications import process_follow_user


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

    if instance.content_type.model == 'look':
        process_comment_look_created.delay(instance.content_object.user, request.user, instance)
        process_comment_look_comment.delay(instance.content_object.user, request.user, instance)

    elif instance.content_type.model == 'product':
        process_comment_product_comment.delay(None, request.user, instance)
        process_comment_product_wardrobe.delay(None, request.user, instance)

comments_signals.comment_was_posted.connect(comments_handler)

#
# Follow handlers
#

def post_save_follow_handler(sender, **kwargs):
    """
    Post save handler for follow objects. Updates followers count on user
    profile and attempts to notify users about this new follow object.
    """
    instance = kwargs['instance']
    if not hasattr(instance, 'user') and instance.content_type == ContentType.objects.get_for_model(instance.user):
        return

    try:
        recipient = User.objects.get(pk=instance.object_id)
        process_follow_user.delay(recipient, instance.user, instance)
    except User.DoesNotExist:
        return

    apparel_profile = recipient.get_profile()
    apparel_profile.followers_count = apparel_profile.followers_count + 1
    apparel_profile.save()

def pre_delete_follow_handler(sender, **kwargs):
    """
    Post save handler for follow objects. Updates followers count on user
    profile.
    """
    instance = kwargs['instance']
    try:
        user = User.objects.get(id=instance.object_id)
    except User.DoesNotExist:
        return

    apparel_profile = user.get_profile()
    apparel_profile.followers_count = apparel_profile.followers_count - 1
    apparel_profile.save()

    Action.objects.filter(actor_object_id=instance.user.pk,
                          actor_content_type=instance.content_type,
                          target_object_id=instance.object_id,
                          target_content_type=instance.content_type,
                          verb='started following').delete()

post_save.connect(post_save_follow_handler, sender=Follow)
pre_delete.connect(pre_delete_follow_handler, sender=Follow)


#
# Delete follows and actions when a user is deleted.
#

def delete_user_followings(signal, instance, **kwargs):
    """
    This signal attempts to delete any followings which is related to Follow
    through a generic relation.
    """
    Follow.objects.filter(
        object_id=instance.pk,
        content_type=ContentType.objects.get_for_model(instance)
        ).delete()
    Follow.objects.filter(user=instance).delete()

# XXX: If actions get missing, look here...
def delete_object_activities(sender, instance, **kwargs):
    """
    This signal attempts to delete any activity which is related to Action
    through a generic relation. This should keep the Action table sane.
    """
    Action.objects.filter(
        action_object_object_id=instance.pk,
        action_object_content_type=ContentType.objects.get_for_model(instance)
        ).delete()
    Action.objects.filter(
        actor_object_id=instance.pk,
        actor_content_type=ContentType.objects.get_for_model(instance)
        ).delete()
    Action.objects.filter(
        target_object_id=instance.pk,
        target_content_type=ContentType.objects.get_for_model(instance)
        ).delete()


# FIXME: Move these to actstream?
post_delete.connect(delete_user_followings, sender=User)
post_delete.connect(delete_object_activities, sender=User)
