import urllib2, os, sys, logging
from datetime import datetime
import tempfile



def fetch(url, localpath=None, username=None, password=None):
    """
    Retrieves given URL and stores it in the given location. The path of the
    downloaded file is returned. If localpath is not defined, a temporary path
    is generated.
    """
    
    if not localpath:
        (fh, localpath) = tempfile.mkstemp(prefix='ar_importer_', suffix='.tmp')
        local_fh = os.fdopen(fh, 'w')
    else:
        local_fh = open(localpath, 'w')
    
    f = urllib2.urlopen(url)
    
    local_fh.write(f.read())
    local_fh.close()
    local_fh = None
    
    return localpath
