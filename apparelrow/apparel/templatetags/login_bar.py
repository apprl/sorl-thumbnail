from django.template import Library
from django.utils.translation import ugettext

register = Library()

@register.inclusion_tag('apparel/tags/login_bar.html')
def login_bar(request_path):
    text = ugettext('Discover fashion selected by bloggers, your friends & other stylemakers.')
    disabled = False

    if request_path.startswith('/product'):
        text = ugettext('Sign up to get sale alerts when the price drops on products you like!')
    elif request_path.startswith('/accounts'):
        disabled = True

    return {'text': text, 'disabled': disabled}
