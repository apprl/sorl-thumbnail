import codecs, cStringIO, sys, re, csv
import traceback

# FIXME: Find out why this module cannot be named "csv" and rename it

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
        
        # FIXME: This is an odd case. There's an array with one element (that is
        # and empty string) keyed on None. Is that a weird side effect of the parser?
        
        if None in row:
            del row[None]
        
        return dict([(k, self.from_latin(v)) for (k, v) in row.items()])

    def from_latin(self, s):
        return u'' if s is None else unicode(s, "utf-8") 

    def __iter__(self):
        return self
