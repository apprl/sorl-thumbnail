import urllib

from django.core.urlresolvers import reverse
from django.db.models.loading import get_model

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

        self.mapping_model = get_model('theimp', 'AffiliateMapping')

    def get_commission_junction_url(self, campaign_id, url):
        return 'http://www.anrdoezrs.net/click-%s-10916893?URL=%s' % (campaign_id, url)

    def get_affiliate_window_url(self, campaign_id, url):
        pass

    def get_zanox_url(self, campaign_id, url):
        pass

    def get_tradedoubler_url(self, campaign_id, url):
        pass

    def get_linkshare_url(self, campaign_id, url):
        pass

    def get_apprl_url(self, store_id, url):
        return 'http://apprl.com%s?store_id=%s&url=%s' % (reverse('advertiser-link'), store_id, url)

    def __call__(self, scraped_item, parsed_item, vendor_id):
        if 'buy_url' in scraped_item:
            parsed_item['buy_url'] = scraped_item['buy_url']

            return parsed_item

        if 'url' in scraped_item:
            url_function = self.affiliate_url.get(scraped_item.get('affiliate'), None)
            if url_function:
                encoded_url = urllib.quote(scraped_item.get('url', ''), '')
                try:
                    identifier = self.mapping_model.objects.get(vendor_id=vendor_id).identifier
                except self.mapping_model.DoesNotExist:
                    identifier = None

                if identifier:
                    parsed_item['buy_url'] = url_function(identifier, encoded_url)
                else:
                    self.delete_value(parsed_item, 'buy_url')
            else:
                self.delete_value(parsed_item, 'buy_url')


            #if scraped_item['vendor'] == 'sunpocket':
                #parsed_item['buy_url'] = self.get_commission_junction_url('116587', encoded_url)

            #elif scraped_item['vendor'] == 'acne':
                ## TODO: get campaign key for acne
                #parsed_item['buy_url'] = self.get_commission_junction_url('116587', encoded_url)

            #elif vendor == 'oki-ni':
                #parsed_item['buy_url'] = 'http://www.awin1.com/pclick.php?p=%s&a=115076&m=%s' % (encoded_url, '2083')

            #else:
                #self.delete_value(parsed_item, 'buy_url')

        return parsed_item
