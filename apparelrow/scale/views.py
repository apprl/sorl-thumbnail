from django.http import HttpResponsePermanentRedirect, HttpResponseNotFound
from django.core.files.storage import default_storage

from sorl.thumbnail.main import DjangoThumbnail

import re


def thumb(request, size, path):
    if re.match(r'^https?://', path):
        # FIXME: This isn't very elagant. Would be nice to redirect this outside
        # of here. Perhaps possible to do this in the urls.py
        if request.GET:
            path += '?' + request.GET.urlencode()
        return HttpResponsePermanentRedirect(path)
    
    if not default_storage.exists(path):
        return HttpResponseNotFound()
    
    m = re.match('^(\d+)(?:x(\d+))?$', size)
    size_group = m.groups() if m.group(2) else (m.group(1), m.group(1))
    
    extension = None
    if request.GET.get('trans'):
        path, extension = get_transparent(path)
    
    opts = None
    if request.GET.get('crop'):
        opts = ('crop',)
    
    thumbnail = DjangoThumbnail(path, size_group, extension=extension, opts=opts) 
    
    # FIXME: Is it possible to do a URL re-write here instead of sending back
    # a location header to the client?
    response = HttpResponsePermanentRedirect(thumbnail.absolute_url)
    response['Expires'] = 'never'
    return response
