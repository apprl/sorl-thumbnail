import urlparse
from product_match.models import UrlDetail, UrlVendorSpecificParams


def match_product(product, computed_url, param):
    # This method will add product id and url detail to the url details table
    parsed_url = urlparse.urlparse(computed_url)
    domain = parsed_url.netloc

    url_details = UrlDetail.objects.create(product_id=product.id, url=computed_url, domain=domain, path=parsed_url.path,
                                           query=parsed_url.query, fragment=parsed_url.fragment)
    url_details.save()

    url_vendor_specific_params = UrlVendorSpecificParams.objects.create(domain=domain, parameter_name=param)
    url_vendor_specific_params.save()


def match_urls(external_url, param):
    parsed_url = urlparse.urlparse(external_url)

    if param:
        parameter = urlparse.parse_qs(parsed_url.query)[param]
        external_url_computed = parsed_url.scheme + '://' + parsed_url.netloc + parsed_url.path + '?' + param + '=' + \
                                parameter[0]

    else:
        external_url_computed = parsed_url.scheme + '://' + parsed_url.netloc + parsed_url.path
        if external_url_computed.endswith('/'):
            external_url_computed = external_url_computed.rstrip('/')

    product_id = UrlDetail.objects.filter(url=external_url_computed).values_list('product_id', flat=True).first()

    return product_id


def get_vendor_params(domain):
    param = UrlVendorSpecificParams.objects.filter(domain=domain).values_list('param_id_name', flat=True).first()
    return param
