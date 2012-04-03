from django.template import Library
from sorl.thumbnail.conf import settings as sorl_settings
from sorl.thumbnail.images import ImageFile
from sorl.thumbnail import default
from sorl.thumbnail.parsers import parse_geometry
from sorl.thumbnail.templatetags.thumbnail import safe_filter

register = Library()

@safe_filter(error_output='auto')
@register.filter
def positive_margin(file_, geometry_string):
    """
    Returns the calculated margin for an image and geometry
    """
    if not file_ or sorl_settings.THUMBNAIL_DUMMY:
        return 'auto'
    margin = [0, 0, 0, 0]
    image_file = default.kvstore.get_or_set(ImageFile(file_))
    x, y = parse_geometry(geometry_string, image_file.ratio)
    ex = x - image_file.x
    margin[3] = ex / 2
    margin[1] = ex / 2
    if ex % 2:
        margin[1] += 1
    ey = y - image_file.y
    margin[0] = ey / 2
    margin[2] = ey / 2
    if ey % 2:
        margin[2] += 1
    return ' '.join(['%spx' % (n if n > 0 else 0,) for n in margin])
