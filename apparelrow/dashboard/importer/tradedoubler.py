import requests
import xmltodict

from dashboard.importer.base import BaseImporter

class TradedoublerImporter(BaseImporter):

    url = 'http://reports.tradedoubler.com/pan/aReport3Key.action?reportName=aAffiliateEventBreakdownReport&columns=timeOfVisit&columns=timeOfEvent&columns=timeInSession&columns=lastModified&columns=epi1&columns=eventName&columns=pendingStatus&columns=siteName&columns=graphicalElementName&columns=productName&columns=productNumber&columns=productNrOf&columns=productValue&columns=affiliateCommission&columns=link&columns=leadNR&columns=orderNR&columns=pendingReason&columns=orderValue&startDate=2012-11-01&endDate=2012-11-30&metric1.lastOperator=/&currencyId=SEK&event_id=0&pending_status=1&organizationId=1524134&includeWarningColumn=true&metric1.summaryType=NONE&latestDayToExecute=0&metric1.operator1=/&breakdownOption=1&reportTitleTextKey=REPORT3_SERVICE_REPORTS_AAFFILIATEEVENTBREAKDOWNREPORT_TITLE&setColumns=true&metric1.columnName1=orderValue&metric1.columnName2=orderValue&decorator=popupDecorator&metric1.midOperator=/&dateSelectionType=1&sortBy=timeOfEvent&filterOnTimeHrsInterval=false&customKeyMetricCount=0&applyNamedDecorator=true&key=1730ee2a8d57884222a7ab24872c8def&format=XML'

    def get_data(self, start_date, end_date):
        response = requests.get(self.url)
        data = xmltodict.parse(response.text.encode('utf-8'))
        for row in data['report']['matrix']['rows']['row']:
            yield dict(row)
