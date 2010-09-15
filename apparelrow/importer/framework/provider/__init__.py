import datetime, os, logging, re

from django.conf import settings

from importer.framework import fetcher

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
    
    
    Synopsis
    
        provider = load_provider('grandpa')
        provider.run(from_warehouse=True, date=datetime.now()) 
    
    """
    
    def __init__(self, feed, **kwargs):
        self.feed      = feed
        self.name      = re.sub(r'[^a-z0-9_]', '_', feed.vendor.name.lower())
        self.file      = None
        self.extension = None
    
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
    
    
    def run(self, from_warehouse=False, for_date=None, **kwargs):
        """
        Entry point for the import process. This will retrieve the file from
        the Internet or the warehouse, then hand it to the process() method
        for parsing.     
        
         - from_warehouse  - load the file from the warehouse, not the url property
         - for_date        - use this as_of_date. Format: YYYY-MM-DD
        
        Other parameters are passed on unchanged to process.
        """
        
        self.fetch(from_warehouse=from_warehouse, for_date=for_date)
        return self.process(**kwargs)
    
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
                # 17 = file or directory already exists. 
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
        
    def process(self, **kwargs):
        """
        Processes the file and calls the data mapper for each record
        """
        # FIXME: Let this be fatal
        raise Exception("process() has to be implemented by subclass")

