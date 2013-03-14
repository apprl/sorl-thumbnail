import logging, sys

from apparelrow.importer.tests.api import *
from apparelrow.importer.tests.mapper import *
from apparelrow.importer.tests.models import *
from apparelrow.importer.tests.provider import *
from apparelrow.importer.tests.fxrates import *

if 'test' in sys.argv:
    logging.disable(logging.CRITICAL)
