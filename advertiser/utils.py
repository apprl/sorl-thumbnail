import urllib

from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.db.models import get_model, Sum
from django.conf import settings
from django.core.mail import mail_managers



def get_transactions(store):
    Transaction = get_model('advertiser', 'Transaction')
    transactions = Transaction.objects.filter(status=Transaction.ACCEPTED,
                                              store_id=store.identifier,
                                              is_paid=False,
                                              invoice__isnull=True)

    return transactions


def calculate_balance(store_id):
    Transaction = get_model('advertiser', 'Transaction')
    Store = get_model('advertiser', 'Store')
    try:
        balance = Transaction.objects.filter(store_id=store_id,
                                             status=Transaction.ACCEPTED,
                                             is_paid=False) \
                                     .aggregate(balance=Sum('commission')) \
                             .get('balance', 0)
        if not balance:
            balance = 0
        store = Store.objects.get(identifier=store_id)
        old_balance = store.balance
        store.balance = -balance
        store.save()

        if old_balance >= -settings.APPAREL_ADVERTISER_MINIMUM_STORE_INVOICE and \
                        store.balance <= -settings.APPAREL_ADVERTISER_MINIMUM_STORE_INVOICE:
            mail_managers('Store invoice', 'Now you can create a StoreInvoice for the store %s' % store_id)

        return balance
    except Store.DoesNotExist:
        pass


def make_advertiser_url(store_id, url, request=None):
    if request:
        return request.build_absolute_uri('%s?store_id=%s&url=%s' % (reverse('advertiser-link'), store_id, urllib.quote(url, '')))

    site_object = Site.objects.get_current()
    base_url = 'http://%s%s' % (site_object.domain, reverse('advertiser-link'))

    return '%s?store_id=%s&url=%s' % (base_url, store_id, urllib.quote(url, ''))
