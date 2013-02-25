import logging
import json
from pprint import pformat

from django.template import Library, Variable, TemplateSyntaxError, Node, VariableDoesNotExist
from django import template
from django.template.defaultfilters import linebreaksbr
from django.utils.html import escape
from django.utils.timesince import timesince
from django.utils.translation import ugettext as _
from django.utils.formats import number_format
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.urlresolvers import reverse
from django.template.defaultfilters import stringfilter
from django.utils.html import urlize
from django.utils.safestring import mark_safe
from django.contrib.staticfiles.storage import staticfiles_storage

from apparel.models import ProductLike, LookLike

register = Library()

@register.inclusion_tag('apparel/tags/facebook_button.html', takes_context=True)
def facebook_button(context, text=None):
    """
    Facebook button templatetag.

    Make sure that the translation for a custom text is picked up correctly.
    """
    facebook_icon = staticfiles_storage.url('images/facebook-icon.png')
    next = None
    if 'next' in context:
        next = context['next']

    if text is None:
        text = _('Connect with Facebook')
    else:
        text = _(text)

    return dict(next=next, text=text, facebook_icon=facebook_icon, request=context['request'])


@register.inclusion_tag('apparel/tags/apparel_facebook_button.html', takes_context=True)
def apparel_facebook_button(context, image=None):
    if not 'request' in context:
        raise AttributeError, 'Please add the ``django.core.context_processors.request`` context processors to your settings.TEMPLATE_CONTEXT_PROCESSORS set'
    logged_in = context['request'].user.is_authenticated()
    if 'next' in context:
        next = context['next']
    else:
        next = None
    if image is not None:
        button = staticfiles_storage.url('images/' + image)
    else:
        button = staticfiles_storage.url('images/fblogo.png')
    return dict(next=next, logged_in=logged_in, button=button, request=context['request'])


@register.filter
def category_descendants_id(category, include_self=True):
    """
    Takes a category (MPTT model) and returns a string with alla descendants id
    including itself separated with comma.
    """
    return ','.join([str(cat.id) for cat in category.get_descendants(include_self=include_self)])

@register.filter
def likes_product(user, product):
    """
    Takes a user model and returns a like object for a specific product.
    """
    if user and user.is_authenticated():
        try:
            return ProductLike.objects.get(user=user, product=product, active=True)
        except ObjectDoesNotExist, MultipleObjectsReturned:
            pass

    return False

@register.filter
def likes_look(user, look):
    """
    Takes a user model and returns a like object for a specific look.
    """
    if user and user.is_authenticated():
        try:
            return LookLike.objects.get(user=user, look=look, active=True)
        except ObjectDoesNotExist, MultipleObjectsReturned:
            pass

    return False


# FIXME: When we've bumped up Django, we should replace the use of these two
# tags with the operator support in the {% if %} template tag:
#   {% if 'me' in list %}...{% endif %}
# same as
#   {% ifinlist 'me' list %} ... {% endifinlist %}
# but alot better

@register.tag(name='ifinlist')
@register.tag(name='ifnotinlist')
def do_ifinlist(parser, token):
    """
    >>> from django.template.loader import Template, Context
    >>> from apparel.templatetags import apparel_extras
    >>> c = Context({ 'a_list': ['one', 'two', 'three', 'four'], 'a_value': 'one', 'another_value': 'six', 'none_list': None})
    >>> # Variable in context exists in list
    >>> t = Template("{% load apparel_extras %}{% ifinlist a_value a_list %}True{% endifinlist %}")
    >>> t.render(c)
    u'True'

    >>> # Constant declared with quotes exists in list
    >>> t = Template("{% load apparel_extras %}{% ifinlist 'one' a_list %}True{% endifinlist %}")
    >>> t.render(c)
    u'True'

    >>> # Constant declared with double quotes exists in list
    >>> t = Template('{% load apparel_extras %}{% ifinlist "two" a_list %}True{% endifinlist %}')
    >>> t.render(c)
    u'True'

    >>> # Constant doesn't exist in list
    >>> t = Template('{% load apparel_extras %}{% ifinlist "nineteen" a_list %}True{% endifinlist %}')
    >>> t.render(c)
    u''

    >>> # Variable doesn't exist in list
    >>> t = Template('{% load apparel_extras %}{% ifinlist another_value a_list %}True{% endifinlist %}')
    >>> t.render(c)
    u''

    >>> # List is None
    >>> t = Template('{% load apparel_extras %}{% ifinlist "two" none_list %}True{% endifinlist %}')
    >>> t.render(c)
    u''

    >>> # Wrong number of arguments (one)
    >>> t = Template('{% load apparel_extras %}{% ifinlist a_list %}True{% endifinlist %}')
    Traceback (most recent call last):
        ...
    TemplateSyntaxError: u'ifinlist' tag takes two arguments

    >>> # Wrong number of arguments (three)
    >>> t = Template('{% load apparel_extras %}{% ifinlist "one" "three" a_list %}True{% endifinlist %}')
    Traceback (most recent call last):
        ...
    TemplateSyntaxError: u'ifinlist' tag takes two arguments

    >>> # Variable doesn't exist
    >>> t = Template('{% load apparel_extras %}{% ifinlist "one" what_list %}True{% endifinlist %}')
    >>> t.render(c)
    u''

    >>> # Negation
    >>> t = Template('{% load apparel_extras %}{% ifnotinlist "nine" a_list %}True{% endifnotinlist %}')
    >>> t.render(c)
    u'True'

    >>> t = Template('{% load apparel_extras %}{% ifnotinlist "two" a_list %}True{% endifnotinlist %}')
    >>> t.render(c)
    u''
    """

    try:
        tag_name, the_value, the_list = token.split_contents()
    except ValueError, e:
        raise TemplateSyntaxError, '%r tag takes two arguments' % token.split_contents()[0]

    nodelist = parser.parse(('end%s' % tag_name,))
    parser.delete_first_token()

    if the_value[0] == the_value[-1] and the_value[0] in ('"', "'"):
        is_constant = True
        the_value = the_value[1:-1]
    else:
        is_constant = False

    return IfInListNode(
        nodes       = nodelist,
        the_list    = the_list,
        the_value   = the_value,
        is_constant = is_constant,
        negate      = True if tag_name == 'ifnotinlist' else False,
    )


class IfInListNode(Node):
    def __init__(self, **kwargs):
        self.a_list  = Variable(kwargs['the_list'])
        self.a_value = kwargs['the_value'] if kwargs['is_constant'] else Variable(kwargs['the_value'])
        self.nodes   = kwargs['nodes']
        self.negate  = kwargs['negate']


    def render(self, context):

        try:
            the_list  = self.a_list.resolve(context)
            the_value = self.a_value.resolve(context) if isinstance(self.a_value, Variable) else self.a_value
        except VariableDoesNotExist, e:
            logging.debug(e)
            return ''

        if not the_list:
            return ''

        if the_value in the_list:
            return '' if self.negate else self.nodes.render(context)

        return self.nodes.render(context) if self.negate else ''

@register.tag(name='calc_half')
def do_calc_half(parser, token):
    """
    Used to calculate what half of two values are. If anyone knows how to make simple expressions in a template, remove this. It's ugly
    """
    try:
        tag_name, var1, var2 = token.split_contents()
    except ValueError, e:
        logging.exception(e)
        raise template.TemplateSyntaxError, "%r tag requires a list as single argument" % token.contents.split()[0]

    return CalcHalfNode(var1, var2)

class CalcHalfNode(Node):
    def __init__(self, var1, var2, **kwargs):
        self.a = Variable(var2)
        self.b = Variable(var1)

    def render(self, context):
        l = [int(self.a.resolve(context)), int(self.b.resolve(context))]
        return int((max(*l) - min(*l)) / 2)



@register.filter('as_list')
def as_list(o):
    """ Returns the object as a list, if it isn't already one. Tuples are converted
    to lists
    >>> from django.template.loader import Template, Context
    >>> from apparel.models import Product
    >>> from apparel.templatetags import apparel_extras
    >>> c = Context({'v1': ('b', 'c',), 'v2': "hello", 'v3': [1, 2, 3]})
    >>> t = Template('{% load apparel_extras %}{{ v1|as_list }}')
    >>> t.render(c)
    u'[&#39;b&#39;, &#39;c&#39;]'

    >>> t = Template('{% load apparel_extras %}{{ v2|as_list }}')
    >>> t.render(c)
    u'[&#39;hello&#39;]'

    >>> t = Template('{% load apparel_extras %}{{ v3|as_list }}')
    >>> t.render(c)
    u'[1, 2, 3]'

    """
    if isinstance(o, tuple):
        return list(o)
    if isinstance(o, list):
        return o

    return [o]

@register.filter('class_name')
def class_name(o):
    """ Outputs class name of given object (if it is one)
    >>> from django.template.loader import Template, Context
    >>> from apparel.models import Product
    >>> from apparel.templatetags import apparel_extras
    >>> c = Context({'p': Product(), 's': "hello"})
    >>> t = Template('{% load apparel_extras %}{{ p|class_name }}')
    >>> t.render(c)
    u'Product'

    >>> t = Template('{% load apparel_extras %}{{ o|class_name }}')
    >>> t.render(c)
    u'str'

    """
    try:
        return mark_safe(o.__class__.__name__)
    except:
        return ''


@register.filter(is_safe=True)
def apprl_intcomma(value):
    if value:
        return number_format(value, use_l10n=False, force_grouping=True)
    else:
        return ''


@register.filter(name='since')
def since(date):
    since = timesince(date)
    return "%s %s" % (since.split(",")[0], _("ago"))


def export_as_json(o):
    """Renders the given object as JSON. Any Django objects will be exported
    >>> from django.template.loader import Template, Context
    >>> c = Context({'p': {'gunnar': True}})
    >>> t = Template('{% load apparel_extras %}{{ p|export_as_json }}')
    >>> t.render(c)
    u'{"gunnar": true}'
    """

    try:
        return mark_safe(json.dumps(o))
    except Exception, e:
        logging.error('Error while exporting object to JSON in template')
        logging.debug('Object: ', pformat(o))
        logging.exception(e)

        return ''

register.filter('export_as_json', export_as_json)


#
# This is taken from http://www.djangosnippets.org/snippets/743/ and should
# probably not be included in a live release
#

def rawdump(x):
    if hasattr(x, '__dict__'):
        d = {
            '__str__':str(x),
            '__unicode__':unicode(x),
            '__repr__':repr(x),
        }
        d.update(x.__dict__)
        x = d
    output = pformat(x)+'\n'
    return output

def dump(x):
    return mark_safe(linebreaksbr(escape(rawdump(x))))

register.filter('rawdump', rawdump)
register.filter('dump', dump)

def getdictattribute(value, arg):
    """
    Gets a dict attribute of an object dynamically from a string name
    """
    if arg in value:
        return value[arg]
    else:
        return settings.TEMPLATE_STRING_IF_INVALID

register.filter('getdictattribute', getdictattribute)

@register.simple_tag
def selected_url(request, *args):
    for pattern in args:
        if pattern == '/':
            if request.path.startswith('/men') or request.path.startswith('/women'):
                return 'selected'
            elif request.path == pattern:
                return 'selected'
        elif pattern == '/profile':
            slug = '--------------------------------------'
            if request.user.is_authenticated():
                slug = request.user.slug
            if not request.path.startswith('/profile/%s' % (slug,)) and not request.path.startswith('/profile/settings') and request.path.startswith(pattern):
                return 'selected'
        else:
            if request.path.startswith(pattern):
                return 'selected'

    return ''

@register.simple_tag
def selected_reverse(request, url):
    path = request.path
    if path == reverse(url):
        return 'selected'
    return ''

@register.simple_tag
def change_gender_url(request, current_gender, gender):
    """
    Calculate new url from current gender and the gender to be.
    """
    if current_gender == 'M':
        current_gender = 'men'
    elif current_gender == 'W':
        current_gender = 'women'
    else:
        current_gender = False

    return reverse('shop-%s' % (gender,))

@register.simple_tag
def gender_url(gender, named_url):
    """
    Reverse named_url with correct gender.
    """
    if gender == 'M':
        return reverse('%s-men' % (named_url,))
    elif gender == 'W':
        return reverse('%s-women' % (named_url,))

    return reverse(named_url)

@register.filter
def urlize_target_blank(value, limit=None, autoescape=None):
    return mark_safe(urlize(value, trim_url_limit=limit, nofollow=True, autoescape=autoescape).replace('<a', '<a target="_blank"'))
urlize_target_blank.is_safe = True
urlize_target_blank.needs_autoescape = True
urlize_target_blank = stringfilter(urlize_target_blank)


@register.simple_tag
def internal_referral_url(url, sid):
    """
    Reverse named_url with correct gender.
    """
    if sid:
        return '%s?sid=%s' % (url, sid)

    return url
