from django.template import Library
from django.utils.translation import ugettext

register = Library()

@register.inclusion_tag('apparel/tags/login_bar.html')
def login_bar(request_path):
    text = ugettext('Follow our stylemakers, bloggers & brands to discover fashion from the world\'s best online stores.')
    disabled = False

    if request_path.startswith('/product'):
        text = ugettext('Sign up to get sale alerts when the price drops on products you like!')
    elif request_path.startswith('/accounts') or request_path.startswith('/partner'):
        disabled = True

    return {'text': text, 'disabled': disabled}
