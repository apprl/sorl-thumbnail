import requests
import xmltodict

from dashboard.importer.base import BaseImporter

class CJImporter(BaseImporter):

    api_key = '008765b01c28856695bf9e6d1cf5a964c828bd64e087f52702d89cf427ba83cdeba00854d1b2ed9151887662aad9d9871c15a21e7bc0d97214d51648835c533a33/7ff6c059ec861fad39dbce3e0783a02778317f8ca19235db7fc3df11493ad6bb1189e6776f22d162c90449ae44dd21331c04606bf8d3aee2e4645f7de06b6571'

    def get_data(self):
        headers = {'authorization': self.api_key}
        response = requests.get('https://commission-detail.api.cj.com/v3/commissions?date-type=posting&start-date=2012-11-27&end-date=2012-12-26', headers=headers)
        data = xmltodict.parse(response.text)
        for row in data['cj-api']['commissions']['commission']:
            yield row
