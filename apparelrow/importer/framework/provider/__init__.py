import datetime, os, logging, re

from django.conf import settings

from importer.framework import fetcher, parser
from apparelrow.importer.api import API, SkipProduct, ImporterException

def load_provider(name, feed):
    module = __import__('importer.framework.provider.%s' % name, fromlist = ['Provider'])   
    
    return module.Provider(feed)

class Provider(object):
    """
    Base class for data providers.
    
    Fields:
     - feed         importer.models.VendorFeed instance
     - file         File handle pointing to the downloaded feed file
     - name         Name of the module the provider belongs to
     - extension    File extensions used when saving the file
     - mapper       Data mapper class
    
    
    Synopsis
    
        provider = load_provider('grandpa')
        provider.run(from_warehouse=True, date=datetime.now()) 
    
    """
    
    def __init__(self, feed, **kwargs):
        self.feed      = feed
        self.name      = re.sub(r'[^a-z0-9_]', '_', feed.vendor.name.lower())
        self.file      = None
        self.extension = None
        self.mapper    = None
    
    def __del__(self, *args, **kwargs):
        if self.file and not self.file.closed:
            self.file.close()
    
    @property
    def url(self):
        return self.feed.url
    
    @property
    def username(self):
        return self.feed.username
    
    @property
    def password(self):
        return self.feed.password
    
    
    def run(self, from_warehouse=False, for_date=None):
        """
        Entry point for the import process. This will retrieve the file from
        the Internet or the warehouse, then hand it to the process() method
        for parsing.     
        
         - from_warehouse  - load the file from the warehouse, not the url property
         - for_date        - use this as_of_date. Format: YYYY-MM-DD
        
        """
        
        self.fetch(from_warehouse=from_warehouse, for_date=for_date)
        return self.process()
    
    def fetch(self, from_warehouse=False, for_date=None):
        """
        Retrieves a file from the Internet, stores it in the warehouse and 
        opens it for reading. The open file object is stored in the file property
        """
        
        # FIXME: 
        #  If anyone needs to override "fetch", it might be a good idea to
        #  move the warehouse bit out so it can be re-used. It won't really
        #  change between providers.
        
        if not for_date:
            for_date = datetime.utcnow()
        
        date = for_date.strftime('%Y-%m-%d')
        path = os.path.join(
            settings.APPAREL_IMPORTER_WAREHOUSE,
            self.name,
            '%s.%s' % (date, self.extension) if self.extension else date
        )
        
        try:
            os.makedirs(os.path.split(path)[0])
            logging.debug("Created warehouse dir %s" % os.path.split(path)[0])
        except OSError, e:
            if not e.errno == 17:
                # 17 = file or directory already exists. Is there a constant for this?
                # Ignore these errors, re-throw all others
                raise
        
        if from_warehouse:
            logging.debug("Reading file from warehouse %s" % path)
        else:
            logging.info("Downloading %s to %s" % self.url, path)
            logging.debug("Storing file in warehouse at %s" % path)
            fetcher.fetch(self.url, path, self.username, self.password)
        
        self.file = open(path, 'r')
        return True
        
    def process(self):
        """
        Processes the file and calls the data mapper for each record. This will
        in turn call import_data with the mapped record
        
        """
        # FIXME: Let this be fatal
        raise Exception("process() has to be implemented by subclass")
    
    def import_data(self, data):
        """
        Imports the data into Apparel using the API
        """
        p = None
        prod_id = data['product']['product-id'] if 'product' in data and 'product-id' in data['product'] else '[unknown]'

        
        try:
            p = API(import_log=self.feed.latest_import_log).import_dataset( data )
        
        except SkipProduct, e:
            self.feed.latest_import_log.messages.create(
                status='info', 
                message="Skipping product\nProduct: %s\nError:%s" % (prod_id, e)
            )
            logging.info('Record skipped: %s', e)
        
        except ImporterException, e:
            self.feed.latest_import_log.messages.create(
                status='error', 
                message="Product skipped due to unexpected errors\nProduct: %s\nError:%s" % (
                    prod_id, e
                )
            )
        
        except Exception, e:
            # FIXME: No need to add anything here as the process will terminate
            logging.critical('Translation failed with uncaught exception: %s', e)
            self.feed.latest_import_log.messages.create(
                status='error', 
                message="Aborting import due to unhandled error.\nProduct: %s\nError:%s" % (
                    prod_id, e
                )
            )
            raise 
        else:
            # FIXME: Should we count number of products imported? If so, do this
            # here. Then add it to the ImportLog instance in when process() 
            # finishes in run()
            logging.info('Imported product %s', p)
    


class CSVProvider(Provider):
    """
    A provider that parses CSV files. 
    Example usage:
    
        from importer.framework.parser import utils
        
        class MyProvider(ProviderCSV):
            def __init__(self, *args, **kwargs):
                super(MyProvider, self).__init__(*args, **kwargs)
                self.dialect = utils.CSVPipeDelimited
                self.encoding = 'latin-1',
                self.fieldnames = (
                    'list', 'of', '#ignore1', 'column', '#ignore2', 'headers'
                )
    
    New fields
    
     - fieldnames       List of fieldnames that will map the column values. They need to be unique.
     - dialect          CSV dialect used to parse the source. See importer.framework.parser and csv.Dialect
     - encoding         Defaults to "utf-8".
    
    """
    
    def __init__(self, *args, **kwargs):
        super(CSVProvider, self).__init__(*args, **kwargs)
        
        self.extension  = 'csv'
        self.fieldnames = None
        self.dialect    = None
        self.encoding   = 'utf-8'
    
    def process(self):
        if not self.fieldnames:
            # FIXME: Read first line of CSV file and use as headers
            pass
        
        csv_reader = parser.CSVParser(self.file, 
            dialect=self.dialect, 
            fieldnames=self.fieldnames,
            encoding=self.encoding,
        )
        
        for row in csv_reader:
            # Instantiate mapper
            # map raw data to API-format
            # Import mapped data using API
            mapper = self.mapper(self, row)
            self.import_data( mapper.translate() )




