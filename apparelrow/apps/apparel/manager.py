from apparel.models import *
from django.db import models
from django.db.models import Q

import re
# Create your views here.
from pprint import pprint


class ARSearchManager(models.Manager):
    """
    This Manager adds enables complex searching specifically for the Product
    class.
    """
    
    def from_query(self, qd):
        """
        Returns a QuerySet from the given QueryDict object.
        """
        
        self.expressions = dict(filter(None, map(self.expression_from_item, qd.items())))
        self.order       = self.order_from_pattern(qd.get('o', self.default_order_pattern()))
        
        query = self.create_query()
        
        # FIXME: Get model (Product) from the class this manager is attached to
        # If that is possible
        return Product.objects.filter(query)
    
    
    
    #
    # Following methods should be considrered private to the class
    # (Move them out? Prefix with __?)
    #
    
    def default_order_pattern(self):
        """
        Returns an order pattern used if none was supplied in the original
        query string. The default pattern takes supplied expression lables,
        sorts them and joins them with and.
        """
        
        return 'a'.join(self.expressions.keys())
    
    def expression_from_item(self, pair):
        """
        For each key/value pair (passed a list), inflates the expression to
        dictionary like so:
            
            label: {
                'field':    'Field Name',
                'model':    'Model Name',  # If None, Product is assumed 
                'value':    'Expression value',
                'operand':  'Django QuerySet operator', # http://docs.djangoproject.com/en/dev/ref/models/querysets/#id7
            }
        
        Key: A correctly formatted key looks like this
        
            id:[model.]field[:operator]     
             - "id" has to be numberic
             - "model" is designated by a single letter and is optional
             - "field" is required
             - "operator" defaults to 'exact'
             
            1:m.name:iexact
        
        Value: Value can usually just be anything, but with following operators,
        some special rule applies
        
            in          Comma-separated list with values. 
            range       Split in two at the first found comma
            isnull      1 for true, 0 for false
        
        If the key (pair[0]) does not match an expression, nothing is returned.
        
        If the key, or value, can't be parsed to a valid exception, an InvalidExpression
        exception is raised.
        
        A two-tuple is returned where the first element is the expression ID and
        the second the expression dictionary.
        """
        
        m = re.match(r'(\d+):(\w)\.(.+?)(?::(.+))?$', pair[0])
        if not m:
            return
        
        operator, value = __prepare_op_val(m.group(4), pair[1])
        
        model = django_models.get(m.group(2), raiseException('Unknown model label %s' % m.group(2)))
        
        return (m.group(1), {
            'field':    m.group(3),
            'model':    model,
            'value':    value,
            'operator': operator
        })


    
    def order_from_pattern(self, pattern):
        """
        Returns a list with the sort order. The list contains tuples with grouped
        expressions followed by and operand
        
        The input string should be formatted as follows
        
            [operand]expression_label[,]...
        
        where expression_label is a named expression and operand is 'o' or 'a'. 
        A trailing comma means next option will not be grouped with this one.
        Operand is required for all by the first expression number.
        
        The operand may be followed by an 'n' which negates it.
        
        Examples
        
            a) 1o2,a3o4
            b) 1o2,a3o4o5,an6,a7
        
        Yields
            
            a) [('1', 'o', '2', 'a'), ('3', 'o', '4')]
            b) [(u'1', u'o', u'2', u'a'), (u'3', u'o', u'4', u'o', u'5', u'an'), (u'6', u'a'), (u'7',)]
            
        Which yields the logical query
        
            a) (1 or 2) and (3 or 4)
            b) (1 or 2) and (3 or 4 or 5) and not 6 and 7
        """
        
        # FIXME: We *might* want to return a list of lists, and pop those
        # items when building the django query expression rather than just
        # iterate over them
        
        o = []              # Sort order list
        append = True       # If true, will not group statements
        for (op, oid, group) in re.compile('(^|(?:a|o)n?)(\d)(,)?').findall(pattern):
            if op:
                o[-1] += (op,)
            
            if append:
                o.append((oid,))
            else:
                o[-1] += (oid,)
            
            append = True if group else False

        return o
    
    
    def query_for_expression(expr):
        """
        Returns a Djano Query object (django.models.db.Q) for the given expression
        (as created by expression_from_item)
        """
        
        model = expr.get('model')
        
        if model == 'options':
            # Special case Option, as they go with an explicit type (should correspond to 'field')
            
            return Q(
                        options__option_type__name__iexact=expr.get('field')
                    ) & Q(
                        **{'options__value__%s' % expr.get('operand'): expr.get('value')}
                    )
        
        # Construct a Django Query API expression "model__field__operand" 
        # (model__ might be left out)
        key = '__'.join(filter(None, [model, expr.get('field'), expr.get('operand')]))
        
        return Q(**{str(key): expr.get('value')})



    def create_query(self):
        """
        Returns a django.models.db.Q object representing the expressions handed
        to this instance.
        """
        
        for group_index, group in enumerate(self.order):
            # Create new group Q-expression for groups with first named expression
            
            # FIXME: Wrap this operation in method?
            if not group[0] in self.expressions:
                raise InvalidExpression('No expression labelled %s' % group[0])
            
            grp_query = self.query_for_expression(self.expressions.get(group[0]))
            
            for offset in range(1, len(group), 2):
                exp_op = group[offset:offset + 2]
                if len(exp_op) == 2:
                    # Get pairs of [operand, expression] for group until all expressions
                    # has been exhausted. Join each together with the group_exp using
                    # the operand (exp[0])
                    
                    if not exp_op[1] in self.expressions:
                        raise InvalidExpression('No expression labelled %s' % exp_op[1])

                    # Full expression. Create new Q-expression and add it to the
                    # group expression                
                    q = self.query_for_expression(self.expressions.get(exp_op[1]))
                    grp_query = merge_q(grp_query, q, exp[0])
            else:
                # Executed when all expressions in group has been expanded
                if grp_idx == 0:
                    # This is the first group, just assign it to the db query
                    dbqry = grp_query
                else:
                    # Get the last operand (previous group, last element)
                    # Use it to add to the db query
                    op = order[grp_idx - 1][-1]
                    dbqry = merge_q(dbqry, group_exp, op)



# ------------------------------------------------------------------------------
# HELPERS & UTILS
# This stuff should be considered local to this module
# ------------------------------------------------------------------------------
        
        
django_models = {
    'm': 'Manufacturer',
    'o': 'Option',
    'c': 'Category',
}    

django_operators = (
    # FIXME: Can you extract these from the django module that implements them?
    'exact', 'iexact', 'contains', 'icontains', 'in', 'gt', 'gte', 'lt', 'lte', 
    'startswith', 'istartswith', 'endswith', 'iendswith',  'range', 'year',
    'month', 'day', 'week_day', 'isnull', 'search', 'regex', 'iregex',
)

        
def __prepare_op_val(operator, value):
    """
    Private routine. Returns two values; the operator in a form that Django
    accepts and a value formatted to match that operator.
    
    If the operator isn't recogised, or if the value is malformatted, the 
    routine raises an InvalidExpression exception.
    
    """
    
    if not operator:
        operator = 'exact'
    elif not operator in django_operators:
        raise InvalidExpression('Unknown operator %s' % operator)
    
    # Perform special casing for value
    if operator == 'in':
        value = value.split(',')
    
    elif operator == 'range':
        value = value.split(',', 1)
    
    elif operator == 'isnull':
        value = True if operator == 1 else False
    
    # FIXME: Add specific handling for date values etc
    
    return operator, value


def __merge_q_obj(base=base, new=new, operand='a'):
    """
    Takes django.db.models.Q object "new" and adds it to Q object "base" and
    using the logic specified in operand. The resulting Q object is returned.
    
    Supported operands
    
        - 'a'   AND (default)
        - 'an'  AND NOT 
        - 'o'   OR
        - 'on'  OR NOT

    """
    if operand == 'a':
        base &= new
    elif operand == 'o':
        base |= new
    elif operand == 'an':
        base &= ~new
    elif operand == 'on':
        base |= ~new
    
    return base




def raiseException(s):
    """
    This method is just a shorthand for raising InvalidExpression exceptions,
    like this
    
        dict.get('some_key', raiseException('Damn, key not found!!'))
    
    Surely there's a better way of doing this, just fix this and refactor code
    accordingly.
    """
    raise InvalidExpression(v)

class InvalidExpression(Exception):
    pass

