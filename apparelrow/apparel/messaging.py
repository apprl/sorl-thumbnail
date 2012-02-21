import logging

from celery.messaging import establish_connection
from kombu.compat import Publisher, Consumer
from django.db.models.loading import get_model
from haystack import site

logger = logging.getLogger(__name__)

def split_seq(sequence, size):
    return [sequence[i:i+size] for i in xrange(0, len(sequence), size)]

def search_index_update(app_name, model_name, pk):
    """
    Send a message for updating a search index object.
    """
    connection = establish_connection()
    publisher = Publisher(connection=connection,
                          exchange="search_updates",
                          routing_key="update_search_index",
                          exchange_type="direct")

    message = '|'.join([app_name, model_name, str(pk)])
    publisher.send(message)

    publisher.close()
    connection.close()

def process_search_index_updates():
    """
    Process all currently gathered search index updates.
    """
    connection = establish_connection()
    consumer = Consumer(connection=connection,
                        queue="search_updates",
                        exchange="search_updates",
                        routing_key="update_search_index",
                        exchange_type="direct")

    updates = {}
    messages = {}
    for message in consumer.iterqueue(limit=1000):
        app_name, model_name, pk = message.body.split('|')
        pk = int(pk)

        key = '%s:%s' % (app_name, model_name)
        if key in updates:
            updates[key]['pks'].add(pk)
        else:
            model_class = get_model(app_name, model_name)
            search_index = site.get_index(model_class)
            updates[key] = {'model_class': model_class, 'search_index': search_index, 'pks': set([pk])}

        if pk in messages:
            messages[pk].append(message)
        else:
            messages[pk] = [message]

    for key, value in updates.items():
        model_class = value['model_class']
        search_index = value['search_index']
        split_pks = split_seq(list(value['pks']), 500)

        seq = 1
        for pks in split_pks:
            logger.info('processing sequence %s with length %s' % (seq, len(pks)))
            search_index.update_objects(model_class.objects.in_bulk(pks).values())
            for pk in pks:
                for message in messages[pk]:
                    if not message.acknowledged:
                        message.ack()
            seq = seq + 1

    consumer.close()
    connection.close()
