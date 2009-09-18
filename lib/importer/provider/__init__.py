import csv, codecs, cStringIO, sys
import traceback
from importer.fetcher import fetch_source


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
        
    
    
    def fetch(self):
        """
        Retrieve a file from somewhere returns it as an open file handle. 
        
        Returns nothing.
        """
        self.file = fetch_source(self)
    
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
        csv_reader = CSVReader(fh, dialect, **kwargs)
        
        for row in csv_reader:
            # FIXME: Is that generic enough to be in this module
            # Probably best to add an 'default_values' hash as arguments, and 
            # merge the row with keys/values in there
            
            row['vendor_name'] = self.name
            m = mapper(row)
            # FIXME: Wrap this in a try/except clause and log any errors
            m.translate()





# FIXME: Define these in a different namespace, perhaps
# importer.parsers or something

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)
        
    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class CSVReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding. 
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.DictReader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return dict([(k, unicode(v, "utf-8")) for (k, v) in row.items()])

    def __iter__(self):
        return self

