from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse
from django.utils.translation import ugettext
from apparel.models import *
from django.db.models import Q, Max, Min
from django.template.loader import find_template_source
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from apparel.json import encode

import re
import math
# Create your views here.
from pprint import pprint


WIDE_LIMIT = 10 # FIME: Move to application settings fileI

def search(request, model):
    result = None
    klass  = {
        'products'     : 'Product',
        'manufacturers': 'Manufacturer',
        'categories'   : 'Category',
        'vendors'      : 'Vendor',
    }.get(model)
    
    if klass:
        klass  = eval(klass)
        result = klass.objects.search(request.GET)
    else:
        raise Exception('No model to search for')
    
    paginator = Paginator(result, 20) #FIXME: Make results per page configurable

    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        paged_result = paginator.page(page)
    except (EmptyPage, InvalidPage):
        paged_result = paginator.page(paginator.num_pages)

    #FIXME: We don't return the paged result because it's not JSON serializable
    return HttpResponse(
        encode(result),
        mimetype='text/json'
    )


def wide_search(request):
    query  = request.GET.get('s')
    result = {
        'products': Product.objects.filter(product_name__icontains=query, description__icontains=query)[:WIDE_LIMIT],
        'manufacturers': Manufacturer.objects.filter(name__icontains=query)[:WIDE_LIMIT],
        'categories': Category.objects.filter(name__icontains=query)[:WIDE_LIMIT],
        'vendors': Vendor.objects.filter(name__icontains=query)[:WIDE_LIMIT],
    }

    return HttpResponse(
        encode(result),
        mimetype='text/json'
    )
    
def filter(request):
    pricerange = VendorProduct.objects.aggregate(min=Min('price'), max=Max('price'))
    pricerange['min'] = int(100 * math.floor(float(pricerange['min']) / 100))
    pricerange['max'] = int(100 * math.ceil(float(pricerange['max']) / 100))
    #FIXME: Create a generic way of getting relevant templates and putting them into the context
    template_source, template_origin = find_template_source('apparel/fragments/product_small.html')
    products = Product.objects.all()
    paginator = Paginator(products, 20) #FIXME: Make number per page configurable
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        paged_products = paginator.page(page)
    except (EmptyPage, InvalidPage):
        paged_products = paginator.page(paginator.num_pages)
    result = {
        'categories': Category._tree_manager.all(),
        'manufacturers': Manufacturer.objects.all(),
        'genders': {
            'M': ugettext('Male'),
            'F': ugettext('Female'),
            'U': ugettext('Unisex'),
            #FIXME: Maybe do this a little nicer
        },
        'pricerange': pricerange,
        'products': paged_products,
        'product_template': template_source,
    }
    return render_to_response('filter.html', result)

def looks():
    pass

def looks():
    pass

def looks():
    pass


#
#def translate_http_query(query):
#    
#    def merge_q(base, new, op):
#        if exp[0] == 'a':
#            base &= new
#        elif exp[0] == 'o':
#            base |= new
#        elif exp[0] == 'an':
#            base &= ~new
#        elif exp[0] == 'on':
#            base |= ~new
#        
#        return base
#
#    def get_order(s):
#        """
#        Returns a list with the sort order. The list contains tuples with grouped
#        expressions followed by and operand
#        
#        The input string should be formatted as follows
#        
#            [operand]expression_label[,]...
#        
#        where expression_label is a named expression and operand is 'o' or 'a'. 
#        A trailing comma means next option will not be grouped with this one.
#        Operand is required for all by the first expression number.
#        
#        Examples
#        
#            a) 1o2,a3o4
#            b) 1o2,a3o4o5,an6,a7
#        
#        Yields
#            
#            a) [('1', 'o', '2', 'a'), ('3', 'o', '4')]
#            b) [(u'1', u'o', u'2', u'a'), (u'3', u'o', u'4', u'o', u'5', u'an'), (u'6', u'a'), (u'7',)]
#            
#        Which yields the logical query
#        
#            a) (1 or 2) and (3 or 4)
#            b) (1 or 2) and (3 or 4 or 5) and not 6 and 7
#        
#        """
#        
#        o = []              # Sort order list
#        append = True       # If true, will not group statements
#        for (op, oid, group) in re.compile('(^|(?:a|o)n?)(\d)(,)?').findall(s):
#            if op:
#                o[-1] += (op,)
#            
#            if append:
#                o.append((oid,))
#            else:
#                o[-1] += (oid,)
#            
#            append = True if group else False
#
#        return o
#        
#    def get_operand(op, value):
#        d = {
#            'eq': 'exact',
#            'ieq': 'iexact',
#            'has': 'contains',
#            'ihas': 'icontains',
#            'in': 'in',
#            'gt': 'gt',
#            'gte': 'gte',
#            'lt': 'lt',
#            'lte': 'lte',
#            'sw': 'startswith',
#            'isw': 'istartswith',
#            'ew': 'endswith',
#            'iew': 'iendswith',
#            'rng': 'range',
#            'yr': 'year',
#            'mn': 'month',
#            'dy': 'day',
#            'wd': 'week_day',
#            'nl': 'isnull',
#            's': 'search',
#            're': 'regex',
#            'ire': 'iregex',
#        }
#        op = d.get(op, 'exact')
#        
#        if op == 'in':
#            value = value.split(',')
#        
#        return op, value
#    
#    def get_model(m):
#        return {
#            'm': 'manufacturer',
#            'v': 'vendor',
#            'c': 'category',
#            'o': 'options',
#        }[m]
#    
#    def dissect_expressions(pair):
#        """
#        For each name/value pair from the QueryDict object, identifies which
#        are expressions and inflates returns a dictionary, labeled by the
#        expression label:
#        
#            
#            label: {
#                'field':    'Field Name',
#                'model':    'Model Name',
#                'value':    'Expression value',
#                'operand':  'Django QuerySet operand', # http://docs.djangoproject.com/en/dev/ref/models/querysets/#id7
#            }
#        
#        """
#        m = re.match(r'(\d+):(p|v|c|o|m)\.(.+?)(?::(.+))?$', pair[0])
#        
#        if not m:
#            return
#        
#        operand, value = get_operand(m.group(4), pair[1])
#        
#        d = {
#            'field': m.group(3),
#            'model': get_model(m.group(2)),
#            'value': value,
#            'operand': operand
#        }
#        
#        return (m.group(1), d)
#    
#    def query_expression(expr):
#        
#        model = expr.get('model')
#        if model == 'options':
#            # Special case Option, as they go with an explicit type (should correspond to 'field')
#            
#            return Q(
#                        options__option_type__name__iexact=expr.get('field')
#                    ) & Q(
#                        **{'options__value__%s' % expr.get('operand'): expr.get('value')}
#                    )
#        
#        # Construct a Django Query API expression "model__field__operand" (model__ might be left out)
#        key = '__'.join(filter(None, [model, expr.get('field'), expr.get('operand')]))
#        
#        return Q(**{str(key): expr.get('value')})
#    
#    dbqry = Q()      # The Django Query
#    order = []       # Order of statements
#    exprs = dict(filter(None, map(dissect_expressions, query.items())))
#    
#    if 'o' in query:
#        order = get_order(query['o'])
#    else:
#        order = map(lambda oid: (oid, 'a'), exprs.keys())
#    
#    for grp_idx, group in enumerate(order):
#        # Create new group Q-expression for groups with first named expression
#        group_exp = query_expression(exprs.get(group[0]))
#        
#        for offset in range(1, len(group), 2):
#            exp = group[offset:offset + 2]
#            if len(exp) == 2:
#                # Get pairs of [operand, expression] for group until all expressions
#                # has been exhausted. Join each together with the group_exp using
#                # the operand (exp[0])
#                
#                expr = exprs.get(exp[1])
#                if not expr:
#                    # FIXME: Reset right?
#                    break
#                
#                # Full expression. Create new Q-expression and add it to the
#                # group expression                
#                q = query_expression(expr)
#                group_exp = merge_q(group_exp, q, exp[0])
#        else:
#            # Executed when all expressions in group has been expanded
#            if grp_idx == 0:
#                # This is the first group, just assign it to the db query
#                dbqry = group_exp
#            else:
#                # Get the last operand (previous group, last element)
#                # Use it to add to the db query
#                op = order[grp_idx - 1][-1]
#                dbqry = merge_q(dbqry, group_exp, op)
#    print "-----------------------------------------------"
#    print str(dbqry)
#    print "-----------------------------------------------"
#    
#    result = Product.objects.filter(dbqry)   
#    pprint(result)
#    return result
    
