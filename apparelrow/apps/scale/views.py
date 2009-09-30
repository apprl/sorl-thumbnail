from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.core.files.storage import default_storage

from sorl.thumbnail.main import DjangoThumbnail

import re


def thumb(request, size, path):
    if not default_storage.exists(path):
        return HttpResponseNotFound()
    
    m = re.match('^(\d+)(?:x(\d+))?$', size)
    size_group = m.groups() if m.group(2) else (m.group(1), m.group(1))
    
    thumbnail = DjangoThumbnail(path, size_group) 
    
    # FIXME: Is it possible to do a URL re-write here instead of sending back
    # a location header to the client?
    return HttpResponseRedirect(thumbnail.absolute_url)

