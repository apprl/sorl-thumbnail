from celery.messaging import establish_connection
from kombu.compat import Publisher, Consumer
from apparelrow.statistics.models import ProductClick

def send_increment_clicks(product_id):
    """
    Send a message for incrementing the click count for an URL.
    """
    connection = establish_connection()
    publisher = Publisher(connection=connection,
                          exchange="clicks",
                          routing_key="increment_click",
                          exchange_type="direct")

    publisher.send(product_id)

    publisher.close()
    connection.close()

def process_clicks():
    """
    Process all currently gathered clicks by saving them to the database.
    """
    connection = establish_connection()
    consumer = Consumer(connection=connection,
                        queue="clicks",
                        exchange="clicks",
                        routing_key="increment_click",
                        exchange_type="direct")

    # First process the messages: save the number of clicks
    # for every URL.
    clicks_for_product = {}
    messages_for_product = {}
    for message in consumer.iterqueue():
        product_id = message.body
        clicks_for_product[product_id] = clicks_for_product.get(product_id, 0) + 1
        # We also need to keep the message objects so we can ack the
        # messages as processed when we are finished with them.
        if product_id in messages_for_product:
            messages_for_product[product_id].append(message)
        else:
            messages_for_product[product_id] = [message]

    # Then increment the clicks in the database so we only need
    # one UPDATE/INSERT for each URL.
    for product_id, click_count in clicks_for_product.items():
        ProductClick.objects.increment_clicks(product_id, click_count)
        # Now that the clicks has been registered for this URL we can
        # acknowledge the messages
        [message.ack() for message in messages_for_product[product_id]]

    consumer.close()
    connection.close()
