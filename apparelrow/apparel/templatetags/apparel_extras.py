import logging
from hanssonlarsson.django.exporter import json
from django.template import Library, Variable, TemplateSyntaxError, Node, VariableDoesNotExist
from django import template
from django.template.defaultfilters import linebreaksbr
from django.utils.html import escape
from django.conf import settings
try:
    from django.utils.safestring import mark_safe
except ImportError: # v0.96 and 0.97-pre-autoescaping compat
    def mark_safe(x): return x
from pprint import pformat

register = Library()



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

register.filter('class_name', class_name)


def export_as_json(o):
    """Renders the given object as JSON. Any Django objects will be exported
    >>> from django.template.loader import Template, Context
    >>> c = Context({'p': {'gunnar': True}})
    >>> t = Template('{% load apparel_extras %}{{ p|export_as_json }}')
    >>> t.render(c)
    u'{"gunnar": true}'
    """
    
    try:
        return mark_safe(json.encode(o))
    except Exception, e:
        logging.error('Error while exporting object to JSON in template')
        logging.debug('Object: ', pformat(o))
        logging.exception(e)
        
        return ''

register.filter('export_as_json', export_as_json)

#
#def split(string):
#    """Splits the given strings on "," and returns a list
#    >>> from django.template.loader import Template, Context
#    >>> c = Context({'s': 'one,two'})
#    >>> t = Template('{% load apparel_extras %}{{ s|split }}')
#    >>> t.render(c)
#    u'[&#39;one&#39;, &#39;two&#39;]'
#    >>> t = Template('{% load apparel_extras %}{{ s|split|first }} - {{ s|split|last }}')
#    >>> t.render(c)
#    u'one - two'
#    """
#    
#    try:
#        return string.split(',')
#    except Exception, e:
#        logging.error('Could not split %s', s)
#        logging.exception(e)
#        
#        return ''
#
#register.filter('split', split)

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
