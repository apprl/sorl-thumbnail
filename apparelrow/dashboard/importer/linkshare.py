import requests
import csv

from dashboard.importer.base import BaseImporter

class LinkshareImporter(BaseImporter):

    username = 'apparelrow'
    password = 'apprl2010'
    network_id = 3

    def get_data(self, start_date, end_date):
        url = 'http://cli.linksynergy.com/cli/publisher/reports/downloadReport.php?bdate=%s&edate=%s&cuserid=%s&cpi=%s&nid=%s' % ('20120101', '20121226', self.username, self.password, self.network_id)

        response = requests.get(url)
        data = response.text.encode('utf-8').splitlines()
        reader = csv.DictReader(data, delimiter='\t', quoting=csv.QUOTE_NONE)
        for row in reader:
            yield row
