import re
from django.db import models
from django.db.models import Q
from django.http import QueryDict
from django.db.models.fields.related import ForeignKey, ManyToManyField, RelatedObject, RelatedField

class SearchManager(models.Manager):
    """
    This Manager adds enables complex searching specifically for the Product
    class.
    """
    
    def search(self, query_dict):
        """
        Returns a QuerySet from the given QueryDict object.
        """
        qp = QueryParser(self.model)
        qs = self.get_query_set()
        
        try:
            qs = qs.filter(qp.parse(query_dict))
        except NoQuery:
            pass
        
        ob = qp.parse_order_by(query_dict)
        if ob: qs = qs.order_by(*ob)
        
        return qs



class FeaturedManager(models.Manager):
    """
    Limits the query set to instances that should be displayed on the front page.
    """
    
    def get_query_set(self):
        return super(FeaturedManager, self).get_query_set().filter(is_featured=True)


class QueryParser():

    model_shorthands = {
        # Maps a short hand to the field used as foreign key on the current object 
        # FIXME: Make this list smart somehow. Properly map for example Vendor > Products and Product > Vendors
        'Manufacturer' : 'm',
        'Option'       : 'o',
        'Category'     : 'c',
        'Product'      : 'p',
        'Vendor'       : 'v',
        'OptionType'   : 't',
        'VendorProduct': 'vp',
        'Look'         : 'l',
    }
    
    django_operators = (
        # FIXME: Can you extract these from the django module that implements them?
        'exact', 'iexact', 'contains', 'icontains', 'in', 'gt', 'gte', 'lt', 'lte', 
        'startswith', 'istartswith', 'endswith', 'iendswith',  'range', 'year',
        'month', 'day', 'week_day', 'isnull', 'search', 'regex', 'iregex',
    )
    
    def __init__(self, model=None):
        self.query_dict    = None
        self.expressions   = None
        self.grouping      = None
        self.model         = model
        self.django_models = {}
        
        #
        # Introspect model to find out what other models somehow relates to this
        # and what field name they have. This then maps to the model_shorthand
        # list and weed out unrelated relations and map the query to the right
        # field
        #
        
        # Allow looking up properties on class being searched
        if self.model.__name__ in self.model_shorthands:
            self.django_models[self.model_shorthands[self.model.__name__]] = (self.model, None)
        
        for field_name in self.model._meta.get_all_field_names():
            field = self.model._meta.get_field_by_name(field_name)[0]
            
            if isinstance(field, RelatedField):
                rel_model = field.rel.to.__name__
                rel_field = field.name
                
            elif isinstance(field, RelatedObject):
                rel_model = field.model.__name__
                rel_field = field.var_name
            else:
                continue
            
            short = self.model_shorthands.get(rel_model)
            
            if short is None:
                continue
            
            self.django_models[short] = (rel_model, rel_field)  
            
    
    
    def parse(self, query_dict=None):
        """
        Parses the given QueryDict object and returns a django.models.Q object.
        """
        
        if not isinstance(query_dict, QueryDict):
            raise NoQuery('query_dict is not a django.http.QueryDict')
        
        self.query_dict  = query_dict
        self.expressions = self.parse_expressions()
        self.grouping    = self.parse_grouping()
        
        query = Q()
        
        for group_index, group in enumerate(self.grouping):
            # Create new group Q-expression for groups with first named expression
            
            grp_query = self.get_expression(label=group[0])
            
            for offset in range(1, len(group), 2):
                op_exp = group[offset:offset + 2]
                if len(op_exp) == 2:
                    # Get pairs of [operand, expression] for group until all expressions
                    # has been exhausted. Join each together with the group_exp using
                    # the operand (exp[0])
                    
                    # Full expression. Create new Q-expression and add it to the
                    # group expression                
                    q         = self.get_expression(label=op_exp[1])
                    grp_query = self.__merge_q_objects(grp_query, q, op_exp[0])
            else:
                # Executed when all expressions in group has been expanded
                if group_index == 0:
                    # This is the first group, just assign it to the db query
                    query = grp_query
                else:
                    # Get the last operand (previous group, last element)
                    # Use it to add to the db query
                    operand = grouping[group_index - 1][-1]
                    query   = self.__merge_q_objects(query, group_exp, operand)
                    
        return query


    
    
    def parse_expressions(self):
        """
        Expands expressions from the key/value pairs in the query_dict property.
        The expanded expression looks like this:
            
            expression_label: {
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
        
        Keys that does not match this pattern are ignored.
        
        Value: Value can usually just be anything, but with following operators,
        some special rule applies
        
            in          Comma-separated list with values. 
            range       Split in two at the first found comma
            isnull      1 for true, 0 for false
        
        """
        
        return dict(
            filter(
                None, 
                [map(self.__parse_key_pair, self.query_dict.items()),
                self.__assemble_expression('0', 'p', 'published', 'exact', 1)]
            ),
        )
    
    
    def parse_grouping(self):
        """
        Returns a list with the order of expressions. The list contains tuples 
        with grouped expressions followed by and operand.
        
        The input string is taken from the value of key 'o' in query_dict, or
        a list of the expression ids.
        
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
        
        pattern  = self.query_dict['o'] if 'o' in self.query_dict else 'a'.join(self.expressions.keys())
        grouping = []      # Sort order list
        append   = True    # If true, will not group statements
        
        #   (operand, expression_label, end of group)
        for (op, oid, group) in re.compile('(^|(?:a|o)n?)(\d)(,)?').findall(pattern):
            if op:
                grouping[-1] += (op,)
            
            if append:
                grouping.append((oid,))
            else:
                grouping[-1] += (oid,)
            
            append = True if group else False

        return grouping
    
    
    def get_expression(self, label=None):
        """
        Returns an expression from expressions for the given label or throwns
        an exception
        """
        try:
            return self.expressions[label]
        except KeyError:
            InvalidExpression('No expression labelled %s' % label)

    
    def parse_order_by(self, query_dict):
        """
        Returns a list of order by extracted from the given order_by field in
        the given query_dict. Returns empty list if no values could be extracted.
        """
        
        order_by = []
        if 'order_by' in query_dict:
            for expr in query_dict['order_by'].split(','):
                m = re.match(r'^(-)?(?:(\w+)\.)?(.+)$', expr)
                if not m: continue

                desc, shorthand, field = m.groups()
                if not field: continue
                
                if shorthand in self.django_models:
                    field = '%s__%s' % (self.django_models[shorthand][1], field)
                
                if desc: field = '-' + field
                
                order_by.append(field)
        
        return order_by
    
    # --------------------------------------------------------------------------
    # PRIVATE ROUTINES
    # --------------------------------------------------------------------------        
    
    def parse_key(self, key):
        """
        >>> from apparel.models import Product
        >>> from apparel.manager import QueryParser
        >>> qp = QueryParser(Product)
        >>> qp.parse_key('1:o.hej:in')
        ('1', 'o', 'hej', 'in')
        
        >>> qp.parse_key('1:o.hej')
        ('1', 'o', 'hej', None)
        
        >>> qp.parse_key('nomatch')
        Traceback (most recent call last):
            ...
        InvalidExpression
        
        """
        m = re.match(r'(\d+):(\w{1,3})\.(.+?)(?::(.+))?$', key)
        if not m:
            raise InvalidExpression()
        
        return m.groups()
    
    # FIXME: Might make this public so it can be properly tested
    def __parse_key_pair(self, pair):
        """
        Like __assemble_expression, but accepts a key/value pair from a query
        that is validated.
        """
        label, short, field, oper = self.parse_key(pair[0]) 
        
        if short.lower() == 'p' and field.lower() == 'published':
            # Do not allow setting the published field of products from query string
            # FIXME: 
            #   Perhaps it would  be an idea to introduce a 'searchable' field
            #   in the models' Meta class to indicate what fields can be specified
            #   in a query
            raise InvalidExpression('Illegal query p.published')
        
        
        return self.__assemble_expression(label, short, field, oper, pair[0])

    
    def __assemble_expression(self, label, short, field, oper, value):
        """
        Assembles a Q-object from the following parts (positional arguments):
        
         label      The query label, used for ordering
         short      Model shorthand (ex. "p" for "Product")
         field      Model field
         oper       Unvalidated operator
         value      Raw unvalidated value
        
        A two-tuple is returned where the first element is the expression label 
        and the second a django.db.models.Q instance for the expression.
        
        None is returned if the key isn't properly formatted
        """
                     
        (model_class, model_field) = self.django_models.get(short, (None, None))
        
        if not model_class:
            raise InvalidExpression('Unknown model label %s' % short)
        
        if self.model and model_class == self.model.__name__:
            model_field = None
        
        operator, value = self.prepare_op_val(oper, value)
        q = None
        
        if model_class == 'Option':
            # Special case option
            q = Q(
                    options__option_type__name__iexact=field
                ) & Q(
                    **{'options__value__%s' % str(operator): value}
                )
        
        else:
            key = '__'.join(filter(None, [model_field, field, operator]))
            q   =  Q(**{str(key): value})
        
        return (label, q)    


    def __merge_q_objects(self, base=None, new=None, operand='a'):
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
    
    
    def prepare_op_val(self, operator, value):
        """
        Private routine. Returns two values; the operator in a form that Django
        accepts and a value formatted to match that operator.
        
        If the operator isn't recogised, or if the value is malformatted, the 
        routine raises an InvalidExpression exception.
        
        """
        
        if not operator:
            operator = 'exact'
        elif not operator in self.django_operators:
            raise InvalidExpression('Unknown operator %s' % operator)
        
        if operator == 'in':
            value = value.split(',')
        
        elif operator == 'range':
            value = value.split(',', 1)
        
        elif operator == 'isnull':
            value = True if operator == 1 else False
        
        # FIXME: Add specific handling for date values etc
        
        return operator, value


class InvalidExpression(Exception):
    pass
    
class NoQuery(Exception):
    pass


