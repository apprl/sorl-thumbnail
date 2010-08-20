import urllib2, os, sys, logging
from datetime import datetime
import tempfile


WAREHOUSE_DIR = os.path.abspath(os.path.dirname(__file__) + '../../../warehouse')

def fetch_source(provider, from_warehouse=False, for_date=None):
    """
    Fetches the source file for the given provider and returns an open file object
    
     - provider         Processor object
     - from_warehouse   If True, the file will not be downloaded from the internet, but read from the archive
     - for_date         date instance (from datetime package) for which the given file will be archived (or read from archive)
                        Defaults for today
    
    """
    if not for_date:
        for_date = datetime.utcnow()
    
    
    # FIXME: Might be worth to do some error handling around this
    date = for_date.strftime('%Y-%m-%d')
    name = '%s.%s' % (date, provider.extension) if provider.extension else date
    wdir = os.path.join(WAREHOUSE_DIR, provider.name)
    
    if not os.path.exists(wdir):
        # Create dir
        logging.debug("Creating warehouse dir %s" % wdir)
        os.makedirs(wdir)
    
    path = os.path.join(wdir, name)
        
    if from_warehouse:
        logging.debug("Reading file from warehouse %s" % path)
    else:
        logging.info("Downloading %s to %s" % (provider.url, path))
        logging.debug("Storing file in warehouse at %s" % path)
        fetch(provider.url, path, provider.username, provider.password)
    
    return path


def fetch(url, localpath=None, username=None, password=None):
    """
    Retrieves given URL and stores it in the given location. The path of the
    downloaded file is returned. If localpath is not defined, a temporary path
    is generated.
    """
    
    # FIXE: Add authentication
    
    if not localpath:
        (fh, localpath) = tempfile.mkstemp(prefix='ar_importer_', suffix='.tmp')
    
    f = urllib2.urlopen(url)
    
    local_fh = os.fdopen(fh, 'w')
    local_fh.write(f.read())
    local_fh.close()
    local_fh = None
    
    return localpath

