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
    
    jQuery('.upload-field input[type=text], .upload-field .button').click(function(e) {
        // Forward click events from the fake controls to file object. This doesn't work in FF
        jQuery('input[type=file]', jQuery(this).parent()).focus();
        return false;
    });
    jQuery('.upload-field input[type=file]').change(function(e) {
        jQuery('input[type=text]', jQuery(this).closest('.upload-field')).val(this.value);
    });
    
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
 *  Search functionality 
 */

ApparelSearch = {
    hide: function() {
        // Hides search result dialog
        jQuery('#search-result').hide();
        jQuery('#search').removeClass('expanded');
    },
    show: function() {
        // Shows search result dialog
        jQuery('#search-result').fadeIn();
        jQuery('#search').addClass('expanded');
    },
    clear: function() {
        // Clears displayed results and cached resultsets and queries
        jQuery('#search-result ul')
            .data('last-query', null)
            .data('last-result', null)
            .empty();
    },
    cancel: function() {
        // Clears and hides all
        this.hide();
        this.clear();
        jQuery('#search > input').val('');
    },
    search: function() {
        // Preforms a search
        
        var s = jQuery('#search > input').val();
        if(s.length == 0)
            return;
        
        ApparelSearch.clear();
        
        ApparelSearch._doSearch({
            model: 'products', 
            query: {
                '1:p.product_name:icontains': s,
                '2:p.description:icontains': s,
                'o': '1o2',
                'size': 8
            },
            selector: '#search-result-products',
            template: 'product_template',
            text: {
                plural: 'Found %(count)s products',
                singular: 'Found %(count)s product'
            }
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
            template: 'look_search_template',
            text: {
                plural: 'Found %(count)s looks',
                singular: 'Found %(count)s look'
            }
        });
        
        ApparelSearch._doSearch({
            model: 'manufacturers', 
            query: {
                '1:m.name:icontains': s,
                'size': 10
            },
            selector: '#search-result-manufacturers',
            template: 'manufacturer_search_template',
            text: {
                plural: 'Found %(count)s matching brands',
                singular: 'Found %(count)s matching brand'
            }
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
                    var args, root;
                    if(opts.template == 'product_template') {
                        // Product template special casing
                        args = { 'product': object };
                        root = list;
                    } else {
                        args = { 'object': object };
                        root = jQuery('<li/>').appendTo(list);
                    }
                    
                    if('score' in object)
                        args.score = interpolate(ngettext("%(count)s like", "%(count)s likes", object.score.score), { count: object.score.score }, true);
                    
                    try {
                        jQuery('#' + opts.template).render(args).appendTo(root);
                    
                    } catch(e) {
                        console.log('Error while rendering template', e);
                    }
                    
                    var item = list.children(':last');
                    item.addClass((i % 2 == 0) ? 'even' : 'odd');
                    if(i == 0)
                        item.addClass('first');
                    if(i == response.object_list.length - 1)
                        item.addClass('last');
                    
                    if(opts.template == 'product_template' && i % 4 == 3)
                        item.addClass('edge');
                });
            
                if(list.children().size() == 0) {
                    console.log('No results');
                }
                
                list.closest('.result-container').children('h2').text(
                    interpolate(
                        ngettext(
                            opts.text.singular, 
                            opts.text.plural, 
                            response.paginator.count
                        ), 
                        { count: response.paginator.count }, 
                        true
                    )
                );
                
                list.data('last-query', opts.query);
                list.data('last-result', response);
            }
        });
    },
    __translations: function() {
        // FIXME: These lines are here so Django can pick them up. They're repeated
        // in the _doSearch function. Find a nicer way of doing this

        ngettext('Found %(count)s product', 'Found %(count)s products', 0);
        ngettext('Found %(count)s look', 'Found %(count)s looks', 0);
        ngettext('Found %(count)s matching brand', 'Found %(count)s matching brands', 0);
    },

};


// DOM bindings

jQuery(document).ready(function() {
    jQuery('#search > input').keyup(function(e) {
        var j = jQuery(this);
        clearTimeout(j.data('tid'));
        
        switch(e.keyCode) {
            case 0: // command+tab
            case 9: // tab
            case 17: // ctrl
            case 18: // alt
            case 224: // command
                return false;
            case 13: // enter
                ApparelSearch.search();
                return false;
            case 27: // escape
                ApparelSearch.cancel();
                return false;
            
            default:
                j.data('tid', setTimeout(ApparelSearch.search, 1000));
        }
    });
    jQuery('#cancel-search')
        .click(function(e) {
            ApparelSearch.cancel();
            return false;
        })
    ;
    jQuery('#search .result-container>h2')
        .click(function(e) {
            var list  = jQuery(this).parent().find('ul:first');
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
