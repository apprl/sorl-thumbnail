import csv, codecs

class CSVPipeDelimited(csv.Dialect):
    lineterminator = '\n'
    delimiter = '|'
    quoting = csv.QUOTE_NONE


class CSVSemiColonDelimited(csv.Dialect):
    lineterminator = '\n'
    delimiter = ';'
    quoting = csv.QUOTE_NONE
    
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

