from __future__ import division
from django import template
import decimal

register = template.Library()

@register.filter(name='commission_rate')
def commission_rate(value, arg):
    if int(arg) == 0:
        return "-"
    else:
        c_rate = 100 * int(value) / int(arg)
        return "%s" % (format(c_rate, '.2f')) +"%"

@register.filter(name='top_five')
def top_five(value):
    return value[:5]

@register.filter(name='floatdot')
def floatdot(value):
    return ("%.2f" % value)

@register.filter(name='decimal_div')
def decimalDiv(value, arg):
    if arg != 0:
        return ("%.2f" % (decimal.Decimal(value)/decimal.Decimal(arg)))
    else:
        return "-"

floatdot.is_safe = True