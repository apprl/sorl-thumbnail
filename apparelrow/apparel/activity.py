import logging

from django.contrib import admin
from django.contrib.comments import signals as comments_signals
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from django.db import models
from apparel.models import *
from actstream import action
from actstream.models import Action

#
# Set up activity handlers.
#
def look_like(sender, instance, **kwargs):
    if not hasattr(instance, 'user'):
        logging.warning('Trying to register an activity, but %s has not user attribute' % instance)
        return

    if instance.active == True:
        action_object = Action.objects.get_or_create(actor_content_type=ContentType.objects.get_for_model(instance.user),
                                                     actor_object_id=instance.user.pk,
                                                     verb='liked_look',
                                                     action_object_content_type=ContentType.objects.get_for_model(instance.look),
                                                     action_object_object_id=instance.look.pk)
    else:
        action_object = Action.objects.filter(actor_object_id=instance.user.pk,
                                              verb='liked_look',
                                              action_object_content_type=ContentType.objects.get_for_model(instance.look),
                                              action_object_object_id=instance.look.pk)
        action_object.delete()

def look_like_delete(sender, instance, **kwargs):
    if not hasattr(instance, 'user'):
        logging.warning('Trying to remove an activity, but %s has not user attribute' % instance)
        return
    action_object = Action.objects.filter(actor_object_id=instance.user.pk,
                                          verb='liked_look',
                                          action_object_content_type=ContentType.objects.get_for_model(instance.look),
                                          action_object_object_id=instance.look.pk)
    action_object.delete()


models.signals.post_save.connect(look_like, sender=LookLike)
models.signals.pre_delete.connect(look_like_delete, sender=LookLike)

#
# Product like activity handlers
#
def product_like(sender, instance, **kwargs):
    if not hasattr(instance, 'user'):
        logging.warning('Trying to register an activity, but %s has not user attribute' % instance)
        return

    if instance.active == True:
        action_object = Action.objects.get_or_create(actor_content_type=ContentType.objects.get_for_model(instance.user),
                                                     actor_object_id=instance.user.pk,
                                                     verb='liked_product',
                                                     action_object_content_type=ContentType.objects.get_for_model(instance.product),
                                                     action_object_object_id=instance.product.pk)
    else:
        action_object = Action.objects.filter(actor_object_id=instance.user.pk,
                                              verb='liked_product',
                                              action_object_content_type=ContentType.objects.get_for_model(instance.product),
                                              action_object_object_id=instance.product.pk)
        action_object.delete()

def product_like_delete(sender, instance, **kwargs):
    if not hasattr(instance, 'user'):
        logging.warning('Trying to remove an activity, but %s has not user attribute' % instance)
        return

    action_object = Action.objects.filter(actor_object_id=instance.user.pk,
                                          verb='liked_product',
                                          action_object_content_type=ContentType.objects.get_for_model(instance.product),
                                          action_object_object_id=instance.product.pk)
    action_object.delete()


models.signals.post_save.connect(product_like, sender=ProductLike)
models.signals.pre_delete.connect(product_like_delete, sender=ProductLike)

#
# Comment activity handler
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

#
# Look activity handler
#

def post_save_handler(sender, **kwargs):
    instance = kwargs['instance']
    if not hasattr(instance, 'user'):
        logging.warning('Trying to register an activity on post_save, but %s has not user attribute' % instance)
        return
    
    if not kwargs['created']:
        return
    
    verb = 'created'

    action.send(
        instance.user, 
        verb=verb,
        action_object=instance
    )


models.signals.post_save.connect(post_save_handler, sender=Look)

def pre_delete_handler(sender, **kwargs):
    instance = kwargs['instance']
    if not hasattr(instance, 'user'):
        logging.warning('Trying to remove an activity on pre_delete, but %s has not user attribute' % instance)
        return

    verb = 'created'

    product_content_type = ContentType.objects.get_for_model(Product)
    user_content_type = ContentType.objects.get_for_model(User)
    look_content_type = ContentType.objects.get_for_model(Look)

    for look_component in instance.components.select_related('product'):
        product = look_component.product
        action_object = Action.objects.filter(actor_content_type=user_content_type,
                                              actor_object_id=instance.user.pk,
                                              target_content_type=look_content_type,
                                              target_object_id=instance.pk,
                                              action_object_content_type=product_content_type,
                                              action_object_object_id=product.pk)
        action_object.delete()

    action_object = Action.objects.filter(actor_object_id=instance.user.pk,
                                          verb=verb,
                                          action_object_content_type=ContentType.objects.get_for_model(instance),
                                          action_object_object_id=instance.pk)
    action_object.delete()

models.signals.pre_delete.connect(pre_delete_handler, sender=Look)

def look_product_addhandler(sender, **kwargs):
    """
    Stores an action when a new look component containing a product is added.
    """
    instance = kwargs['instance']
    if not hasattr(instance.look, 'user'):
        logging.warning('Trying to register an activity on post_save, but %s has not user attribute' % instance)
        return

    if 'created' in kwargs and kwargs['created']:
        action.send(
            instance.look.user,
            verb='added',
            action_object=instance.product,
            target=instance.look
        )

def look_product_delhandler(sender, **kwargs):
    """
    Deletes an action when a look component containing a product is removed.
    """
    instance = kwargs['instance']
    if not hasattr(instance.look, 'user'):
        logging.warning('Trying to remove an activity on pre_delete, but %s has not user attribute' % instance)
        return

    product_content_type = ContentType.objects.get_for_model(Product)
    user_content_type = ContentType.objects.get_for_model(User)
    look_content_type = ContentType.objects.get_for_model(Look)

    action_object = Action.objects.filter(actor_content_type=user_content_type,
                                          actor_object_id=instance.look.user.pk,
                                          target_content_type=look_content_type,
                                          target_object_id=instance.look.pk,
                                          action_object_content_type=product_content_type,
                                          action_object_object_id=instance.product.pk,
                                          verb='added')
    action_object.delete()

models.signals.post_save.connect(look_product_addhandler, sender=LookComponent)
models.signals.pre_delete.connect(look_product_delhandler, sender=LookComponent)
