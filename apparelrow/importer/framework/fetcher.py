import urllib2, urlparse, os, sys, logging, tempfile, re
from datetime import datetime

from django.conf import settings
import subprocess

logger = logging.getLogger('apparel.importer.fetcher')


def fetch(url, localpath=None, username=None, password=None, decompress=None):
    """
    Retrieves given URL and stores it in the given location. The path of the
    downloaded file is returned. If localpath is not defined, a temporary path
    is generated.
    
    If username or password is defined, the Basic Authentication headers are
    added to the request.
    """
    
    if username or password:
        bits = urlparse.urlparse(url)
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, '%s://%s' % (bits.scheme, bits.netloc), username, password)
        
        urllib2.install_opener(
            urllib2.build_opener(
                urllib2.HTTPBasicAuthHandler(password_mgr)
            )
        )
        
        logging.debug('Added Basic Authentication header. Username %s' % username)
    
    if not localpath:
        if decompress and decompress in settings.APPAREL_DECOMPRESS_SUFFIX:
            suffix = settings.APPAREL_DECOMPRESS_SUFFIX[decompress]
        else:
            m = re.search(r'.+(\.\w+)(?:\?|$)', url)
            suffix = m.group(1) if m else '.tmp'
        
        (fh, localpath) = tempfile.mkstemp(prefix='ar_importer_', suffix=suffix)
        local_fh = os.fdopen(fh, 'w')
    else:
        local_fh = open(localpath, 'w')
    
    f = urllib2.urlopen(urllib2.quote(url, ":/&?="))
    
    local_fh.write(f.read())
    local_fh.close()
    local_fh = None
    
    return localpath



def fetch_feed(url, path, from_warehouse=False, username=None, password=None, decompress=None):
    """
    Fetches a feed file from "url" to "path". Arguments
    
        from_warehouse          Fetch the file from the warehouse instead of URL
        username                Username to use when requesting file
        password                Password to use when requesting file
        decompress              If set, will attempt to decompress the file before
                                returning it.  
    
    """
    try:
        os.makedirs(os.path.split(path)[0])
        logger.debug("Created warehouse directory %s" % os.path.split(path)[0])
    except OSError, e:
        if not e.errno == 17:
            # 17 = file or directory already exists. Is there a constant for this?
            # Ignore these errors, re-throw all others
            raise
    
    if from_warehouse:
        logger.debug("Reading file from warehouse %s" % path)
        if not os.path.exists(path):
            raise Exception('File %s not in warehouse. Try importing file vendor instead' % path)
    else:
        logger.info("Downloading %s" % url)
        temppath = fetch(url, username=username, password=password, decompress=decompress)
        
        if decompress:
            temppath = Decompressor(decompress).decompress(temppath)
        
        logger.debug('Moving feed file %s to warehouse: %s' % (temppath, path)) 
        os.rename(temppath, path)
    
    return path



class Decompressor():
    # FIXME: Add better error handling and move this to separate module
    """
    decompressed_path = Decompressor('gzip').decompress(original_path)
    """
    def __init__(self, utility):
        if not utility in settings.APPAREL_DECOMPRESS_UTILS:
            raise Exception('Unsupported decompress utility "%s"' % utility)
        
        self.utility = utility
        self.bin     = settings.APPAREL_DECOMPRESS_UTILS[utility]
    
    def decompress(self, path):
        """
        Run a utility to extract path. Returns the path to the decompressed file
        """
        
        if not hasattr(self, 'decompress_%s' % self.utility):
            raise Exception('The Decompressor() class does not know how to decompress %s' % self.utility)
        
        logging.debug('Decompressing %s using %s' % (path, self.bin))
        return getattr(self, 'decompress_%s' % self.utility)(path)
        
    def decompress_gzip(self, path):
        ret = subprocess.call([self.bin, path])
        
        if not ret == 0:
            raise Exception('Could not execute %s %s' % (self.bin, path))
        
        return os.path.splitext(path)[0]
    
    def decompress_zip(self, path):
        result = subprocess.check_output([self.bin, '-o', path])
        match  = re.search(r'inflating: (.+?)\n', result)
        if not match:
            raise Exception('Could not find decompressed file in %s. Output: %s' % (path, result))
        
        return os.path.join(os.path.dirname(path), match.groups(1))

