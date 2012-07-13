import os
from django.core.files.storage import default_storage

def get_transparent(path):
    print 'get_transparent'
    path_and_file, ext = os.path.splitext(path)
    newext = 'png'
    newpath = '%s_transparent%s%s' % (path_and_file, os.extsep, newext)
    if not default_storage.exists(newpath):
        make_transparent(path, newpath)
    return newpath, newext

def make_transparent(path, newpath):
    from PIL import Image
    print 'make_transparent'
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
