import StringIO

from django.conf import settings
from django.db.models.loading import get_model
from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import InMemoryUploadedFile

try:
    from PIL import Image
except ImportError:
    import Image


class Command(BaseCommand):
    args = ''
    help = 'Migrate look collage to use an transparent background image for ratio sizing'

    def handle(self, *args, **options):
        Look = get_model('apparel', 'Look')
        for look in Look.objects.filter(component='C'):
            empty_image = Image.new('RGBA', (look.width, look.height), (255, 255, 255, 0))
            empty_image_io = StringIO.StringIO()
            empty_image.save(empty_image_io, format='PNG')

            empty_image_file = InMemoryUploadedFile(empty_image_io, None, '%s.png' % (look.slug,), 'image/png', empty_image_io.len, None)

            look.image = empty_image_file
            look.image_width = look.width
            look.image_height = look.height

            look.save()
