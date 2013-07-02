import urllib
from urlparse import urlparse, urlunparse

from django.core.urlresolvers import reverse

from theimp.parser.modules import BaseModule


class BuildBuyURL(BaseModule):

    def __init__(self, *args, **kwargs):
        super(BuildBuyURL, self).__init__(*args, **kwargs)

        self.affiliate_url = {
            'cj': self.get_commission_junction_url,
            'affiliatewindow': self.get_affiliate_window_url,
            'zanox': self.get_zanox_url,
            'tradedoubler': self.get_tradedoubler_url,
            'linkshare': self.get_linkshare_url,
            'aan': self.get_apprl_url,
        }

    def get_commission_junction_url(self, campaign_id, url):
        return 'http://www.anrdoezrs.net/click-4125005-%s?URL=%s' % (campaign_id, url)

    def get_affiliate_window_url(self, campaign_id, url):
        return 'http://www.awin1.com/pclick.php?p=%s&a=115076&m=%s' % (url, campaign_id)

    def get_zanox_url(self, campaign_id, url):
        parsed_url = urlparse(url)
        path_query = urlunparse(('', '', parsed_url.path, '', parsed_url.query, ''))

        return 'http://ad.zanox.com/ppc/?%s&ulp=[[%s]]' % (campaign_id, path_query)

    def get_tradedoubler_url(self, campaign_id, url):
        try:
            program_id, g_id = campaign_id.split('|')
        except ValueError:
            return None

        return 'http://clk.tradedoubler.com/click?p=%s&a=1853028&g=%s&url=%s' % (program_id, g_id, url)

    def get_linkshare_url(self, campaign_id, url):
        return 'http://click.linksynergy.com/deeplink?id=oaQeNCJweO0&mid=%s&murl=%s' % (campaign_id, url)

    def get_apprl_url(self, store_id, url):
        return 'http://apprl.com%s?store_id=%s&url=%s' % (reverse('advertiser-link'), store_id, url)

    def __call__(self, scraped_item, parsed_item, vendor):
        if 'buy_url' in scraped_item:
            parsed_item['buy_url'] = scraped_item['buy_url']

            return parsed_item

        if 'url' in scraped_item:
            url_function = self.affiliate_url.get(scraped_item.get('affiliate'), None)
            if url_function:
                encoded_url = urllib.quote(scraped_item.get('url', ''), '')
                if vendor.affiliate_identifier:
                    buy_url = url_function(vendor.affiliate_identifier, encoded_url)
                    if buy_url:
                        parsed_item['buy_url'] = buy_url
                    else:
                        self.delete_value(parsed_item, 'buy_url')
                else:
                    self.delete_value(parsed_item, 'buy_url')
            else:
                self.delete_value(parsed_item, 'buy_url')

        return parsed_item
