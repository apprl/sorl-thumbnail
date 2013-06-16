import urllib


def generate_buy_url(vendor, url):
    urlencoded = urllib.quote(url, '')

    # Commission junction

    if vendor == 'sunpocket':
        return 'http://www.anrdoezrs.net/click-%s-10916893?URL=%s' % ('116587', urlencoded)

    # Affiliate window

    elif vendor == 'oki-ni':
        return 'http://www.awin1.com/pclick.php?p=%s&a=115076&m=%s' % (urlencoded, '2083')

    # TODO: add every vendor here

    return url
