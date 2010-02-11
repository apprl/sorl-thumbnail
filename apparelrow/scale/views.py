from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.core.files.storage import default_storage

from sorl.thumbnail.main import DjangoThumbnail

import re
import os


def thumb(request, size, path):
    if not default_storage.exists(path):
        return HttpResponseNotFound()
    
    m = re.match('^(\d+)(?:x(\d+))?$', size)
    size_group = m.groups() if m.group(2) else (m.group(1), m.group(1))
    
    extension = None
    if request.GET.get('trans'):
        path, extension = get_transparent(path)

    thumbnail = DjangoThumbnail(path, size_group, extension=extension) 
    
    # FIXME: Is it possible to do a URL re-write here instead of sending back
    # a location header to the client?
    return HttpResponseRedirect(thumbnail.absolute_url)

def get_transparent(path):
    path_and_file, ext = os.path.splitext(path)
    newext = 'png'
    newpath = '%s_transparent%s%s' % (path_and_file, os.extsep, newext)
    if not default_storage.exists(newpath):
        make_transparent(path, newpath)
    return newpath, newext

def make_transparent(path, newpath):
    from PIL import Image
    img = Image.open(default_storage.open(path))
    img = img.convert('RGBA')
    pixels = img.load()
    for y in range(img.size[1]):
        for x in range(img.size[0]):
            if pixels[x, y] == (255, 255, 255, 255):
                pixels[x, y] = (255, 255, 255, 0)
    output = default_storage.open(newpath, 'wb')
    img.save(output, 'PNG')
    output.close()
