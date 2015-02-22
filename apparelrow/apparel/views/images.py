from django.conf import settings
from django.views.generic import View
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.core.files.base import ContentFile

from apparelrow.apparel.models import TemporaryImage
from apparelrow.apparel.utils import JSONResponse

from StringIO import StringIO
from PIL import Image
from PIL.ExifTags import TAGS
from time import time

class TemporaryImageView(View):

    def get(self, request, *args, **kwargs):
        return JSONResponse([])

    def post(self, request, *args, **kwargs):
        f = self.request.FILES.get('image_file')
        if not f:
            return HttpResponse('')

        temp_image = TemporaryImage(image=f)
        temp_image.save()

        image = Image.open(ContentFile(temp_image.image.read()))

        exifdict = image._getexif() if hasattr(image, '_getexif') else None
        if exifdict is not None and len(exifdict):
            for k in exifdict.keys():
                if k in TAGS.keys() and TAGS[k] == 'Orientation':
                    if exifdict[k] == 6:
                        image = image.transpose(Image.ROTATE_270)
                    elif exifdict[k] == 8:
                        image = image.transpose(Image.ROTATE_90)
                    elif exifdict[k] == 3:
                        image = image.transpose(Image.ROTATE_180)
                    tmp_io = StringIO()
                    image.save(tmp_io, 'JPEG')
                    temp_image.image.save('%s_%d' % (temp_image.image.name, time()), ContentFile(tmp_io.getvalue()))
                    temp_image.save()

        data = [{'id': temp_image.pk,
                 'name': f.name,
                 'url': temp_image.image.url,
                 'thumbnail_url': '',
                 'delete_url': reverse('temporary-image-delete', kwargs={'pk': temp_image.pk}),
                 'delete_type': 'DELETE'}]
        response = JSONResponse(data)
        response['Content-Disposition'] = 'inline; filename=files.json'

        return response

    def delete(self, request, pk):
        temp_image = TemporaryImage.get(pk=pk)
        temp_image.delete()
        if request.is_ajax():
            response = JSONResponse(True)
            response['Content-Disposition'] = 'inline; filename=files.json'

            return response

        return HttpResponseRedirect(reverse('temporary-image'))
