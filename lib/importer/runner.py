import sys, os
from optparse import OptionParser, OptionError
from importer.provider import load_provider

from pprint import pprint

try:
    import pinax
except ImportError:
    # Yieeehaaa! No godforsaken pinax to configure!
    pass
else:
    import settings
    
    sys.path.insert(0, os.path.join(settings.PINAX_ROOT, "apps"))
    sys.path.insert(0, os.path.join(settings.PROJECT_ROOT, "apps"))



def run(provider_name):
    processor = load_provider(provider_name)
    
    if not processor:
        return
    
    processor.fetch()
    processor.process()


if __name__ == '__main__':
    op = OptionParser(description = 'Import a product feed into the Apparel Row system')
    op.add_option('-p', '--provider', dest='provider', help='Name of data provider')
    
    try:
        (options, args) = op.parse_args()
    except OptionError, e:
        op.error(e)
    
    if not options.provider:
        op.error('Require provider name (-p)')
    
    run(options.provider)
