import urllib

from django.db.models.loading import get_model

from theimp.parser.modules import BaseModule


class BuildBuyURL(BaseModule):

    def get_commission_junction_url(self, campaign_id, url):
        return 'http://www.anrdoezrs.net/click-%s-10916893?URL=%s' % (campaign_id, url)


    def __call__(self, scraped_item, parsed_item, vendor_id):
        if 'buy_url' in scraped_item:
            parsed_item['buy_url'] = scraped_item['buy_url']

            return parsed_item

        if 'url' in scraped_item:
            encoded_url = urllib.quote(scraped_item['url'], '')

            if scraped_item['vendor'] == 'sunpocket':
                parsed_item['buy_url'] = self.get_commission_junction_url('116587', encoded_url)

            elif scraped_item['vendor'] == 'acne':
                # TODO: get campaign key for acne
                parsed_item['buy_url'] = self.get_commission_junction_url('116587', encoded_url)

            elif vendor == 'oki-ni':
                parsed_item['buy_url'] = 'http://www.awin1.com/pclick.php?p=%s&a=115076&m=%s' % (encoded_url, '2083')


        return parsed_item
