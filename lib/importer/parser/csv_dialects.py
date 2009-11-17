import csv

class PipeDelimited(csv.Dialect):
    lineterminator = '\n'
    delimiter = '|'
    quoting = csv.QUOTE_NONE


class SemiColonDelimited(csv.Dialect):
    lineterminator = '\n'
    delimiter = ';'
    quoting = csv.QUOTE_NONE
