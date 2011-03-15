import logging, sys

from importer.tests.api import *
from importer.tests.mapper import *
from importer.tests.models import *
from importer.tests.provider import *
from importer.tests.fxrates import *

if 'test' in sys.argv:
    logging.disable(logging.CRITICAL)
