from django.template import Library
from django.core.urlresolvers import reverse

from apparel.utils import generate_sid

register = Library()

@register.simple_tag
def buy_url(product_id, vendor, target_user_id=0, page='Default'):
    """
    Append custom SID to every buy URL.
    """
    if target_user_id == '':
        target_user_id = 0

    if page == '':
        page = 'Default'

    return reverse('product-redirect', args=(product_id, page, target_user_id))


@register.simple_tag
def get_sid(target_user_id=0, page='Default'):
    return generate_sid(target_user_id, page)
