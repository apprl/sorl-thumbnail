from django.template import Library
from django.core.urlresolvers import reverse
from django.utils.http import urlquote

from apparel.utils import vendor_buy_url, generate_sid

register = Library()

@register.simple_tag
def buy_url(product_id, vendor, target_user_id=0, page='Default'):
    """
    Append custom SID to every buy URL.
    """
    return '%s?i=%s&u=%s&s=%s&p=%s' % (reverse('product-click-count'),
                                       product_id,
                                       urlquote(vendor_buy_url(product_id, vendor, target_user_id, page)),
                                       target_user_id,
                                       page)


@register.simple_tag
def get_sid(target_user_id=0, page='Default'):
    return generate_sid(target_user_id, page)
