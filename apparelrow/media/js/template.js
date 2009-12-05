jQuery.extend(jQuery.template.regx, {django: /\{\{\s*([\w-\.]+)(?:\|([\w\.]*)(?:\:(.*?)?[\s\}])?)?\s*\}\}/g});
jQuery.template.regx.standard = jQuery.template.regx.django;
var template = {
    /** This function will render objects using template, using the templateContextGetter
     * function to get the properties of the object
     * */
    render: function(element, objects, template, templateContextGetter) {
        jQuery.each(objects, function(i, obj) {
            element.append(template, templateContextGetter(obj)).hide().fadeIn('normal');
        });
    },
    /** getTemplateContext is called with a structure containing information about an object
      * and returns a dictionary where the keys are the full names of the properties, e.g.:
      * 
      * getTemplateContext( {
      *     'product': {
      *         'object': product,
      *         'properties': ['product_image', 'product_name']
      *     },
      *     'category': {
      *         'object': category,
      *         'properties': ['category_name']
      *     }
      * })
      * yields:
      * {
      *     'product.product_name': product.product_name,
      *     'product.product_image': product.product_image,
      *     'category.category_name': category.category_name
      * }
      */
    getTemplateContext: function(objects) {
        result = {};
        jQuery.each(objects, function(object_name, object_meta) {
            jQuery.each(object_meta['properties'], function(i, property) {
                result[object_name + '.' + property] = object_meta['object'][property];
            });
        });
        return result;
    },
};

