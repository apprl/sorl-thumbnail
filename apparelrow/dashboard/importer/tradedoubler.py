import requests
import xmltodict
import dateutil.parser

from dashboard.importer.base import BaseImporter

class TradedoublerImporter(BaseImporter):
    """
    Tradedoubler importer.

    startDate and endDate format is YYYY-MM-DD.
    """
    name = 'Tradedoubler'
    url = 'http://reports.tradedoubler.com/pan/aReport3Key.action?reportName=aAffiliateEventBreakdownReport&columns=timeOfVisit&columns=timeOfEvent&columns=timeInSession&columns=lastModified&columns=epi1&columns=eventName&columns=pendingStatus&columns=siteName&columns=graphicalElementName&columns=productName&columns=productNumber&columns=productNrOf&columns=productValue&columns=affiliateCommission&columns=link&columns=leadNR&columns=orderNR&columns=pendingReason&columns=orderValue&startDate=%s&endDate=%s&metric1.lastOperator=/&currencyId=SEK&event_id=0&pending_status=1&organizationId=1524134&includeWarningColumn=true&metric1.summaryType=NONE&latestDayToExecute=0&metric1.operator1=/&breakdownOption=1&reportTitleTextKey=REPORT3_SERVICE_REPORTS_AAFFILIATEEVENTBREAKDOWNREPORT_TITLE&setColumns=true&metric1.columnName1=orderValue&metric1.columnName2=orderValue&decorator=popupDecorator&metric1.midOperator=/&dateSelectionType=1&sortBy=timeOfEvent&filterOnTimeHrsInterval=false&customKeyMetricCount=0&applyNamedDecorator=true&key=1730ee2a8d57884222a7ab24872c8def&format=XML'

    def map_status(self, status_string):
        # Pending status
        if status_string == 'P':
            return 'P'

        # Declined status
        if status_string == 'D':
            return 'D'

        # Accepted status
        if status_string == 'A':
            return 'C'

        # Incomplete
        return 'I'

    def get_data(self, start_date, end_date):
        url = self.url % (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        response = requests.get(url)
        data = xmltodict.parse(response.text.encode('utf-8'))

        data_row = {}
        for row in data['report']['matrix']['rows']['row']:
            data_row['original_sale_id'] = row['orderNR']
            data_row['affiliate'] = self.name
            _, data_row['vendor'] = self.map_vendor(row['programName'])
            data_row['commission'] = row['affiliateCommission']
            data_row['currency'] = 'SEK'
            data_row['amount'] = row['orderValue']
            data_row['user_id'], data_row['placement'] = self.map_placement_and_user(row['epi1'])
            data_row['status'] = self.map_status(row['pendingStatus'])
            data_row['sale_date'] = dateutil.parser.parse(row['timeOfEvent'])

            yield data_row
