
def get_domain(url):
    parsed_url = urlparse.urlsplit(url)
    domain = parsed_url.netloc
    return domain
