import logging

from celery.messaging import establish_connection
from kombu.compat import Publisher, Consumer
from django.db.models.loading import get_model
from django.contrib.auth.models import User

import profile.notifications

logger = logging.getLogger(__name__)

def send_notification(notification_name, recipient_pk, sender_pk, app_name, model_name, pk):
    """
    Add a possible notification to the message queue.
    """
    if recipient_pk == sender_pk:
        return

    connection = establish_connection()
    publisher = Publisher(connection=connection,
                          exchange='apparel_notification',
                          routing_key='send_notification',
                          exchange_type='direct')

    message = '|'.join([str(x) for x in [notification_name, recipient_pk, sender_pk, app_name, model_name, pk]])
    publisher.send(message)

    publisher.close()
    connection.close()

def process_notification():
    """
    Process all notifications in the message queue
    """
    connection = establish_connection()
    consumer = Consumer(connection=connection,
                        queue='apparel_notification',
                        exchange='apparel_notification',
                        routing_key='send_notification',
                        exchange_type='direct')

    messages = []
    for message in consumer.iterqueue():
        messages.append(message)

    duplicates = set()
    for message in reversed(messages):
        logger.debug('Processing notifcation message: %s' % (message.body,))
        if message.body in duplicates:
            if not message.acknowledged:
                message.ack()
            logger.info('Duplicate entry found for notification message: %s' % (message.body,))
            continue
        duplicates.add(message.body)

        notification_name, recipient_pk, sender_pk, app_name, model_name, pk = message.body.split('|')
        try:
            recipient = User.objects.get(pk=int(recipient_pk))
        except ValueError:
            recipient = None
        except User.DoesNotExist:
            if not message.acknowledged:
                message.ack()
            logger.warning('Recipient user not found, pk = %s' % (recipient_pk,))
            continue

        try:
            sender = User.objects.get(pk=int(sender_pk))
        except ValueError:
            sender = None
        except User.DoesNotExist:
            if not message.acknowledged:
                message.ack()
            logger.warning('Sender user not found, pk = %s' % (sender_pk,))
            continue

        ModelClass = get_model(app_name, model_name)
        try:
            action_object = ModelClass.objects.get(pk=int(pk))
        except ModelClass.DoesNotExist:
            if not message.acknowledged:
                message.ack()
            logger.warning('Action object not found, app_name = %s, model_name = %s, pk = %s' % (app_name, model_name, pk,))
            continue

        try:
            process_notification = getattr(profile.notifications, 'process_%s' % (notification_name,))
        except AttributeError:
            logger.error('No process handler found for notification event %s' % (notification_name,))
            continue

        process_notification(recipient, sender, action_object)

        if not message.acknowledged:
            message.ack()

    consumer.close()
    connection.close()
