import cStringIO, sys, re, csv
from importer.parser.utils import UTF8Recorder

class Parser():
    """
    Base class for parsers.
    """
    
    def __init__(self, f):
        self.file = f
        
    
    def __iter__(self):
        return self

class CSVParser(Parser):
    """
    Simple CSV parser.
    """
    
    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        super(CSVParser, self).__init__(f)
        self.reader = csv.DictReader(UTF8Recoder(self.file, encoding), dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        
        # NOTE: This is an odd case. There's an array with one element (that is
        # and empty string) keyed on None. Is that a weird side effect of the parser?
        
        if None in row:
            del row[None]
        
        return dict([(k, self.from_latin(v)) for (k, v) in row.items()])
    
    def from_latin(self, s):
        return u'' if s is None else unicode(s, "utf-8") 



