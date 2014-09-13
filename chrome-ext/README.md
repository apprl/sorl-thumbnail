APPRL Chrome Extension
======================

Adds an APPRL icon in the address bar. On click it will fetch authentication
status and do a lookup for url and domain to get product data.

Example requests for a click on the extension icon for http://example.com/example:

    GET /backend/authenticated/
    GET /backend/product/lookup/?key=http%3A%2F%2Fexample.com%2Fexample&domain=example.com

If the user is not authenticated a redirect to APPRL login screen will be returned.
