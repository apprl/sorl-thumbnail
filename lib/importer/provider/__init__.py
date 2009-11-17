import traceback
from importer.fetcher import fetch_source
from importer.parser import csv_parser as csv
#pprint(sys.path)

#from importer.parser import csv_parser as csv

def load_provider(name):
    module = __import__('importer.provider.%s' % name, fromlist = ['Provider'])   
    return module.Provider()


class Provider():
    """
    Base class for product providers.
    
    Fields:
     - name          Unique name to identify the provider
     - url           URL to remote file   
     - username      Username if remote site requires authentication
     - password      Password if remote site requires authentication
     - extension     File name extension
    
    """
    def __init__(self, **kwargs):
        self.name      = None
        self.url       = None
        self.username  = None
        self.password  = None
        self.extension = None
        self.file      = None
        
    
    
    def fetch(self, **kwargs):
        """
        Retrieve a file from somewhere returns it as an open file handle. 
        
        Returns nothing.
        """
        self.file = fetch_source(self, **kwargs)
    
    def process(self):
        """
        Processes.
        """
        # FIXME: Let this be fatal
        raise Exception("process() has to be implemented by subclass")

    
    def process_as_csv(self, dialect=None, mapper=None, **kwargs):
        """
        Process CSV.
        """
        
        print self.file
        fh = open(self.file)
        csv_reader = csv.CSVReader(fh, dialect, **kwargs)
        
        for row in csv_reader:
            # FIXME: Is that generic enough to be in this module
            # Probably best to add an 'default_values' hash as arguments, and 
            # merge the row with keys/values in there
            
            m = mapper(self, row)
            # FIXME: Wrap this in a try/except clause and log any errors
            m.translate()
