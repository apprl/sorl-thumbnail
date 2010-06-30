function increase_counts(counts, new_count) {
    // For each element, set to new_count if available, otherwise increase the current count with 1
    counts.each(function() {
        $(this)
            .hide()
            .html(new_count ? new_count : parseInt($(this).html()) + 1)
            .fadeIn()
            ;
    });
}
jQuery(document).ready(function() {
    // Make all "apparel rows" scrollables
    jQuery('.row').scrollable().end();


    // Adding comments to jquery-tmpl, syntax: {{#}}comment{{/#}} Note: the "" are important
    jQuery.tmplcmd['#'] = {
        prefix: '/*',
        suffix: '*/'
    }
    var likeContainers = 'body.look #content, body.product .product-image';
    jQuery(likeContainers).children('form').hyperSubmit({
        success: function(response, statusText, req, form) {
            // Match "/model/slug/like"
            if(/^\/(\w+)\/([\w-]+)\/like/.test(form.attr('action'))) {
                increase_counts(jQuery('#like-' + RegExp.$1 + '-' + RegExp.$2 + ' > span.count'), response.score.score);
            }
        },
    });
    // Comments posting
    var comment_area = jQuery('#comments-and-links textarea');
    if(comment_area.val() == '')
        jQuery('#comments-and-links button').hide();
    comment_area
        .focus(function() { jQuery('#comments-and-links button').show() })
        .blur(function() { if(jQuery(this).val() == '') jQuery('#comments-and-links button').hide() })
        .autogrow();
    jQuery('#comments-and-links form').hyperSubmit({
        success: function(data, statusText, req) {
            comment_area.val('');
            jQuery('#comments-and-links button').hide();
            jQuery(data.html).hide().appendTo('ul#comments').slideDown('fast');
            increase_counts(jQuery('a.comments > span.count'));
            return false;
        },
    });
    //Hover state for share button
    jQuery('.share').hover(
        function() { jQuery(this).find('ul').show(); }, 
        function() { jQuery(this).find('ul').hide(); }
    );
    jQuery('.share').click(function() { jQuery(this).find('ul').toggle(); return false; })
    
    jQuery('ul.hover-menu li[class!=active]')
        .live('mouseenter', function(e) { 
            jQuery(this).addClass('hover'); 
            return true;
        } )
        .live('mouseleave', function(e) { 
            jQuery(this).removeClass('hover');
            return true; 
        } )
    ;
});


function makeProductTooltip(selector) {
    var q = (typeof selector == 'string')
        ? jQuery(selector)
        : selector;
    
    q.tooltip({
        effect: 'slide',
        relative: true,
        delay: 500,
        offset: [30, 60]
    });
}




/**
 *  Search functionality and HTML bindings
 */

ApparelSearch = {
    hide: function() {
        jQuery('#search-result').hide();
        jQuery('#search').removeClass('expanded');
    },
    show: function() {
        jQuery('#search-result').fadeIn();
        jQuery('#search').addClass('expanded');
    },
    clear: function() {
        jQuery('#search-result ul')
            .data('last-query', null)
            .data('last-result', null)
            .empty();
        jQuery('#search-result .more-results').hide();
    },
    search: function() {
        var s = jQuery('#search > input').val();
        if(s.length == 0)
            return;
        
        ApparelSearch.clear();
        
        // Find products
        
        ApparelSearch._doSearch({
            model: 'products', 
            query: {
                '1:p.product_name:icontains': s,
                '2:p.description:icontains': s,
                'o': '1o2',
                'size': 6
            },
            selector: '#search-result-products',
            template: 'product_search_template'
        });
    
        ApparelSearch._doSearch({
            model: 'looks', 
            query: {
                '1:l.title:icontains': s,
                '2:l.description:icontains': s,
                'o': '1o2',
                'size': 6
            },
            selector: '#search-result-looks',
            template: 'look_search_template'
        });
        
        ApparelSearch._doSearch({
            model: 'manufacturers', 
            query: {
                '1:m.name:icontains': s,
                'size': 10
            },
            selector: '#search-result-manufacturers',
            template: 'manufacturer_search_template'
        });
        
        ApparelSearch.show();
    },
    _doSearch: function(opts) {
        /**
         * Performs an AJAX request for a particular model with specified query
         *
         * Options:
         *  model       Model to search for
         *  query       Query as dict
         *  template    Name of template for rendering results
         *  selector    Selector of UL to add results to
         */
        jQuery.ajax({
            type: 'GET',
            url: '/' + opts.model + '/search',
            dataType: 'json',
            data: opts.query,
            complete: function(request, status) {
                console.log('Do cleanup here (hide "now searching" visual clue and whatever)')
            },
            success: function(response, status, request) {
                if(!response) return;
                var list = jQuery(opts.selector);
                jQuery.each(response.object_list, function(i, object) {
                    try {
                        var args, root;
                        if(opts.template == 'product_search_template') {
                            // Product template special casing
                            args = { 'product': object };
                            root = list;
                        } else {
                            args = { 'object': object };
                            root = jQuery('<li/>').appendTo(list);
                        }
                        
                        jQuery('#' + opts.template).render(args).appendTo(root);
                    } catch(e) {
                        console.log('Error while rendering template', e);
                    }
                });
                
                if(list.children().size() == 0) {
                    console.log('No results');
                } else if(response.paginator.num_pages > 1) {
                    jQuery('.more-results', list.parent()).show();
                }
                
                list.data('last-query', opts.query);
                list.data('last-result', response);
            }
        });
    }
};


jQuery(document).ready(function() {
    jQuery('#search > input').keyup(function(e) {
        // FIXME: Ignore if modifier is used (apart from shift)
        var j = jQuery(this);
        clearTimeout(j.data('tid'));
        
        switch(e.keyCode) {
            case 0: // command+tab
            case 9: // tab
            case 13: // enter
            case 17: // ctrl
            case 18: // alt
            case 224: // command
                return false;
            case 27: // escape
                hideSearch();
                return false;
            
            default:
                j.data('tid', setTimeout(ApparelSearch.search, 1000));
        }
    });
            
    jQuery('#search .more-results')
        .hover(
            function(e) { jQuery(this).addClass('hover') },
            function(e) { jQuery(this).removeClass('hover') }
        )
        .click(function(e) {
            var list  = jQuery(this).siblings('ul');
            var query = list.data('last-query');
            
            switch(list.attr('id')) {
                case 'search-result-products':
                    if(!query) {
                        console.error('Could not find search query');
                        break;
                    }
                    
                    delete(query['size']);
                    var pairs = [];
                    for(var key in query) {
                        pairs.push(
                           encodeURIComponent(key)
                            + '=' 
                            + encodeURIComponent(query[key])
                        );
                    }
                            
                    location.href = '/browse/?' + pairs.join('&');
                    break;
                
                case 'search-result-manufacturers':

                    var s = query['1:m.name:icontains'];
                    location.href = 
                        '/browse/?criterion=manufacturer&'
                        + encodeURIComponent('1:m.name:icontains')
                        + '=' + encodeURIComponent(s)
                        + '&defaults=manufacturer-dialog'
                        + '&defaults=' 
                        + encodeURIComponent('manufacturer-dialog-filter|' + s)
                    
                    break;
                
                default:
                    console.log('No action for ', list.attr('id'));
            }
            
            return false;
        } )
    ;
    } );
