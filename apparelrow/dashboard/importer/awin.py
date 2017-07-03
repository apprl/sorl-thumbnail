import json

'''
*	Understand important steps of AWIN 										CHECK
*	What does transactions means
*	WHat is the difference between reports and transactions
* 	Which fields are necessary for our database
* 	How to map json fields into dbase fields
*	How do I do a request to the page with correct authentication and so forth
* 	How does Json work
*	How does Django work
* 	How does Docker work and how does it start everything
'''

'''
API information
- Name of API: 				Publisher API
- The API uses:				REST as a standard
							oauth2 for authentication
							JSON as the default response data format
- Access:					The API is available via https://api.awin.com
							Please note that only https is supported, no forwarding from http is in place
							Before you can use it you need to create your own oauth2 token via https://ui.awin.com/awin-api
							Please see the wiki page API authentication and authorization for further details.
- Oath2 Token:				d910c415-9306-444f-9feb-52bdcc4e2b20
							Please remember: this token is the only thing you need to access your data via the API. 
							Neither your username nor your password is required. This makes the token a very powerful key, so please make sure it doesn't fall into the wrong hands
- CURL:						http://wiki.awin.com/index.php/API_authentication
							curl -X GET --header 'Accept: application/json' 'https://api.awin.com/accounts?accessToken=<d910c415-9306-444f-9feb-52bdcc4e2b20>'
- Header:					To send your token via the http headers, please use "Authorization" as the key, 
							and "Bearer <addYourTokenHere>" as the value. (Example on postman on website http://wiki.awin.com/index.php/API_authentication)
- Limitation/Throttling: 	To guarantee smooth operation for all our publishers and advertisers, we currently have a throttling in place that limits 
							the number of API requests to 100 API calls per minute per user.

TRANSACTIONS: 
Publishers and advertisers can pull individual transactions, to check the status of the transactions, 
to create own reports, and to pull additional information that can be shared between publishers and 
advertisers via clickref (from publisher to advertiser) and orderRef and custom parameters (from advertiser to publisher)

REPORTS
The advertiser performance report aggregates transactions, clicks and impressions for all advertisers a publisher works with.

TRANSACTIONS HOW IT WORKS
-	How to call it
	https://api.awin.com/publishers/<yourPublisherId>/transactions/?
	startDate=yyyy-MM-ddThh%3Amm%3Ass&endDate=yyyy-MM-ddThh%3Amm%3Ass&timezone=UTC&
	dateType=transaction&status=pending&advertiserId=<advertiserIdForWhichToFilter>

	Example:
	https://api.awin.com/publishers/45628/transactions/?startDate=2017-02-20T00%3A00%3A00&endDate=2017-02-21T01%3A59%3A59&timezone=UTC

TRANSACTIONS RESPONSE
{
    "id": 259630312,
    "url": "http://www.publisher.com",
    "advertiserId": 7052,
    "publisherId": 189069,
    "siteName": "Publisher",
    "commissionStatus": "pending",
    "commissionAmount": {
      "amount": 5.59,
      "currency": "GBP"
    },
    "saleAmount": {
      "amount": 55.96,
      "currency": "GBP"
    },
    "clickRefs": {
      "clickRef": "12345",
      "clickRef2": "22222",
      "clickRef3": "33333",
      "clickRef4": "44444",
      "clickRef5": "55555",
      "clickRef6": "66666"
    },
    "clickDate": "2017-01-23T12:18:00",
    "transactionDate": "2017-02-20T22:04:00",
    "validationDate": null,
    "type": "Commission group transaction",
    "declineReason": null,
    "voucherCodeUsed": false,
    "lapseTime": 2454307,
    "amended": false,
    "amendReason": null,
    "oldSaleAmount": null,
    "oldCommissionAmount": null,
    "clickDevice": "Windows",
    "transactionDevice": "Windows",
    "publisherUrl": "http://www.publisher.com/search?query=dvds",
    "advertiserCountry": "GB",
    "orderRef": "111222333444",
    "customParameters": [
      {
        "key": "1",
        "value": "555666"
      },
      {
        "key": "2",
        "value": "example entry"
      },
      {
        "key": "3",
        "value": "LLLMMMNNN"
      }
    ],
    "transactionParts": [
      {
        "commissionGroupId": 12345,
        "amount": 44.76
      }

      {

        "commissionGroupId": 654321,
        "amount": 11.20

      }


    ],
    "paidToPublisher": false,
    "paymentId": 0,
    "transactionQueryId": 0,
    "originalSaleAmount": null
  }
REPORTS how it works
	GET REPORTS AGGREGATED BY ADVERTISER
						The advertiser performance report aggregates transactions, clicks and impressions for all advertisers a publisher works with.
	How to call it: 	https://api.awin.com/publishers/45628/reports/advertiser?startDate=2017-01-01&endDate=2017-03-17&region=GB&timezone=UTC

REPORT RESPONSE EXAMPLE
{
    "advertiserId": 1001,
    "advertiserName": "Example Advertiser",
    "publisherId": 45628,
    "publisherName": "Example Publisher",
    "region": "GB",
    "currency": "GBP",
    "impressions": 0,
    "clicks": 0,
    "pendingNo": 0,
    "pendingValue": 0,
    "pendingComm": 0,
    "confirmedNo": 0,
    "confirmedValue": 0,
    "confirmedComm": 0,
    "bonusNo": 1,
    "bonusValue": 0,
    "bonusComm": 2500,
    "totalNo": 1,
    "totalValue": 0,
    "totalComm": 2500,
    "declinedNo": 0,
    "declinedValue": 0,
    "declinedComm": 0
  }
'''

'''
in zanox.py _, data_row ['vendor'] = self.map_vendor(row['program']['$']) 
why do we use map_vendor when we can access vendor by row['program']['$'] ? 
'''


def test_parse():
    # hardcoded json object, since awin do not provide us with data yet 3-07-2017

    request_data = '{ "advertiserId": 1001, "advertiserName": "Example Advertiser", "publisherId": 45628, ' \
                   '"publisherName": "Example Publisher", "region": "GB", "currency": "GBP", "impressions": 0,\
                   "clicks": 0, "pendingNo": 0, "pendingValue": 0, "pendingComm": 0, "confirmedNo": 0, "confirmedValue": 0, ' \
                   '"confirmedComm": 0, "bonusNo": 1, "bonusValue": 0, "bonusComm": 2500, "totalNo": 1,\
                   "totalValue": 0, "totalComm": 2500, "declinedNo": 0, "declinedValue": 0, "declinedComm": 0	}'
    report = json.loads(request_data)


    for r in report:
        print('report row data: %s' % r)


test_parse()