from __future__ import division
from django import template

register = template.Library()

@register.filter(name='commission_rate')
def commission_rate(value, arg):
    if int(arg) == 0:
        return "-"
    else:
        return str(100 * int(value) / int(arg))+"%"

@register.filter(name='top_five')
def top_five(value):
    return value[:5]