import urllib2, os, sys, time
from datetime import date
import tempfile


WAREHOUSE_DIR = os.path.abspath(os.path.dirname(__file__) + '../../../warehouse')

def fetch_source(provider, from_archive=False, for_date=date.today().isoformat()):
    """
    Fetches the source file for the given provider and returns an open file object
    
     - provider         Processor object
     - from_archive     If True, the file will not be downloaded from the internet, but read from the archive
     - for_date         Date for which the given file will be archived (or read from archive)
    
    """
    
    # FIXME: Might be worth to do some error handling around this
    name = '%s.%s' % (for_date, provider.extension) if provider.extension else for_date
    wdir = os.path.join(WAREHOUSE_DIR, provider.name)
    
    if not os.path.exists(wdir):
        # Create dir
        print "Creating warehouse dir %s" % wdir
        os.makedirs(wdir)
    
    path = os.path.join(wdir, name)
        
    if not from_archive:
        print "Downloading... %s to %s" % (provider.url, path)
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
    
    local_fh = open(localpath, 'w')
    local_fh.write(f.read())
    local_fh.close()
    local_fh = None
    
    return localpath

