import csv, codecs, cStringIO, sys
import traceback

def load_provider(name):
    #try:
    module = __import__('importer.provider.%s' % name, fromlist = ['Processor'])
    #except:
        # FIXME: Raise fatal exception
    #    
    #    print "Failed to import provider: %s" % sys.exc_info()[1]
    #    return
   
    return module.Processor()


class Processor():
    
    def fetch(self):
        """
        Retrieve a file from somewhere and set the 'file' property of the 
        instance.
        
        Returns nothing.
        """
    
    def process(self):
        """
        Processes.
        """
        # FIXME: Let this be fatal
        raise Exception("process() has to be implemented by subclass")

    
    def process_csv(self, source, dialect=None, mapper=None, **kwargs):
        """
        Process CSV.
        """
        
        csv_reader = CSVReader(source, dialect, **kwargs)
        
        for row in csv_reader:
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

