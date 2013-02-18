from django.db.models import get_model
from django.template.defaultfilters import floatformat
from celery.task import task


@task(name='statistics.tasks.product_buy_click', max_retries=5, ignore_result=True)
def product_buy_click(product_id, referer, ip, user_agent, user_id, page):
    """
    Buy click stats for products
    """
    try:
        product = get_model('apparel', 'Product').objects.get(pk=product_id)
    except get_model('apparel', 'Product').DoesNotExist:
        return

    get_model('statistics', 'ProductClick').objects.increment_clicks(product_id)

    if product.default_vendor:
        vendor = product.default_vendor.vendor
        price = floatformat(product.default_vendor.lowest_price_in_sek, 0)
    else:
        vendor = None
        price = None

    get_model('statistics', 'ProductStat').objects.create(
        action='BuyReferral',
        product=product.slug,
        vendor=vendor,
        price=price,
        user_id=user_id,
        page=page,
        referer=referer,
        ip=ip,
        user_agent=user_agent)
