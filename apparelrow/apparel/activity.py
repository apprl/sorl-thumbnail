from django.contrib import admin
from django.contrib.comments import signals as comments_signals
from django.contrib.contenttypes.models import ContentType

from django.db import models
from apparel.models import *
from actstream import action
from actstream.models import Action
from voting.models import Vote

import logging


#
# Set up activity handlers.
#

def comments_handler(sender, **kwargs):
    if not hasattr(kwargs['request'], 'user'):
        return
    
    action.send(
        kwargs['request'].user, 
        verb='commented', 
        action_object=kwargs['comment']
    )

comments_signals.comment_was_posted.connect(comments_handler)


def post_save_handler(sender, **kwargs):
    instance = kwargs['instance']
    if not hasattr(instance, 'user'):
        logging.warning('Trying to register an activity on post_save, but %s has not user attribute' % instance)
        return
    
    if not kwargs['created']:
        return
    
    verb = 'liked' if isinstance(instance, Vote) else 'created'

    action.send(
        instance.user, 
        verb=verb,
        action_object=instance
    )

models.signals.post_save.connect(post_save_handler, sender=Look)
models.signals.post_save.connect(post_save_handler, sender=Vote)


def post_delete_handler(sender, **kwargs):
    instance = kwargs['instance']
    if not hasattr(instance, 'user'):
        logging.warning('Trying to remove an activity on post_delete, but %s has not user attribute' % instance)
        return

    verb = 'liked' if isinstance(instance, Vote) else 'created'

    action_object = Action.objects.filter(actor_object_id=instance.user.pk,
                                          verb=verb,
                                          action_object_content_type=ContentType.objects.get_for_model(instance),
                                          action_object_object_id=instance.pk)
    action_object.delete()

models.signals.post_delete.connect(post_delete_handler, sender=Look)
models.signals.post_delete.connect(post_delete_handler, sender=Vote)


# TODO: When you can remove products from the wardrobe and remove looks, make sure that this actions is also removed
def m2m_handler(sender, **kwargs):
    """
    Stores an action when an object is added to a manytomany relationship.
    """
    if kwargs['action'] != 'post_add':
        return
    
    instance = kwargs['instance']
    if not hasattr(instance, 'user'):
        logging.warning('Trying to register an activity on m2m_change (%s), but %s has not user attribute' % (sender, instance))
        return
    
    for pk in kwargs['pk_set']:
        action.send(
            instance.user, 
            verb='added', 
            action_object=kwargs['model'].objects.get(pk=pk),
            target=instance
        )

models.signals.m2m_changed.connect(m2m_handler, sender=Wardrobe.products.through)
models.signals.m2m_changed.connect(m2m_handler, sender=Look.products.through)


