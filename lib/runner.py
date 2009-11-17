import sys, os, re, datetime
from optparse import OptionParser, OptionError
from importer.provider import load_provider

#try:
#    import pinax
#except ImportError:
#    # Yieeehaaa! No godforsaken pinax to configure!
#    pass
#else:
#    import settings
#    
#    sys.path.insert(0, os.path.join(settings.PINAX_ROOT, "apps"))
#    sys.path.insert(0, os.path.join(settings.PROJECT_ROOT, "apps"))



def run(provider_name, archive=None, date=None):
    processor = load_provider(provider_name)
    
    if not processor:
        return
    
    processor.fetch(from_warehouse=archive, for_date=date)
    processor.process()


if __name__ == '__main__':
    op = OptionParser(description = 'Import a product feed into the Apparel Row system')
    op.add_option('-p', '--provider', dest='provider', help='Name of data provider')
    op.add_option('-w', '--from_warehouse', dest='from_warehouse', action="store_true", help='Source file will be read from the warehouse')
    op.add_option('-d', '--date', dest='date', help='Date for which to fetch data', default=datetime.datetime.utcnow())

    try:
        (options, args) = op.parse_args()
    except OptionError, e:
        op.error(e)
    
    if not options.provider:
        op.error('Require provider name (-p)')
    
    if isinstance(options.date, basestring):
        m = re.match('^(\d{4})-(\d{2})-(\d{2})$', options.date)
        if not m:
            op.error('date parameter (-d) requires format YYYY-MM-DD')
        
        options.date = datetime.date(*map(lambda s: int(s), m.group(1,2,3)))
    
    run(
        options.provider,
        options.from_warehouse,
        options.date
    )
