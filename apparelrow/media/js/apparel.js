function increase_counts(counts, new_count) {
    // For each element, set to new_count if available, otherwise increase the current count with 1
    counts.each(function() {
        $(this)
            .hide()
            .html(typeof new_count != "undefined" ? new_count : parseInt($(this).html()) + 1)
            .fadeIn()
            ;
    });
}

/**
 * Creates a modal dialog with yes/no as alternatives.
 */
function create_modal_dialog(header, messages, yes_action, no_action) {
    var modal_dialog = jQuery('#error_dialog_template')
        .render({
            modal: true,
            header: header,
            messages: messages,
        })
        .appendTo('body')
        .overlay({
            mask: {
                color: '#000',
                loadSpeed: 200,
                opacity: 0.5
            },
            load: true,
            closeOnClick: false,
            top: 100,
            onClose: function(e) { this.getTrigger().remove() }
        });

    jQuery('.yes', modal_dialog).click(function() { yes_action(jQuery(modal_dialog).overlay()); });
    jQuery('.no', modal_dialog).click(function() { no_action(jQuery(modal_dialog).overlay()); });
}

/**
 * Creates a dialog from html loaded through ajax, only alternativ is close
 */
function create_html_dialog(url_to_html, large_dialog) {
    var dialog = jQuery('<div class="dialog"></div>');

    if(large_dialog) {
        dialog.addClass('large-dialog');
    }

    dialog.load(url_to_html).appendTo('body').overlay({
        mask: {
            color: '#000',
            loadSpeed: 200,
            opacity: 0.5
        },
        load: true,
        closeOnClick: true,
        close: '.close',
        top: 100,
        onClose: function(e) { this.getTrigger().remove() }
    });
}

jQuery(document).ready(function() {
    // Make all "apparel rows" scrollables
    jQuery('.row').scrollable().end();

    // Make all textareas autogrow
    jQuery('textarea').autoResize();

    // All elements with class open-dialog should open a dialog and load html from href-url
    jQuery('.open-dialog').live('click', function(event) {
        create_html_dialog(jQuery(this).attr('href'));
        event.preventDefault();
    });

    jQuery('.open-dialog-large').live('click', function(event) {
        create_html_dialog(jQuery(this).attr('href'), true);
        event.preventDefault();
    });

    // Make sure that a dialog can be closed by the element with class 'close'
    jQuery('.dialog .close').live('click', function(event) {
        $('.dialog').overlay().close();
        event.preventDefault();
    });

    // Adding comments to jquery-tmpl, syntax: {{#}}comment{{/#}} Note: the "" are important
    jQuery.tmplcmd['#'] = {
        prefix: '/*',
        suffix: '*/'
    }

    // Clone products for hovering in browse and search results

    jQuery('form.like').hyperSubmit({
        success: function(response, statusText, req, form) {
            // Match "/model/slug/like"
            var action = form.attr('action');
            var newAction = form.attr('data-alternate-action');
            form.attr('action', newAction).attr('data-alternate-action', action);

            var button = jQuery('button', form);
            var doneText = button.attr('data-done-text');
            var newDoneText = button.attr('data-alternate-done-text');
            var buttonText = button.text();
            var newButtonText = button.attr('data-alternate-text');
            button.attr('data-alternate-text', buttonText)
                  .attr('data-alternate-done-text', doneText)
                  .attr('data-done-text', newDoneText)
                  .text(doneText).delay(1000).text(newButtonText);
            if(/^\/(\w+)\/([\w-]+)\/like/.test(action) && response.success == true) {
                elem = jQuery('#like-' + RegExp.$1 + '-' + RegExp.$2 + ' > span.count');
                elem.text(parseInt(elem.text(), 10) + 1);
            }
            if(/^\/(\w+)\/([\w-]+)\/unlike/.test(action) && response.success == true) {
                elem = jQuery('#like-' + RegExp.$1 + '-' + RegExp.$2 + ' > span.count');
                elem.text(parseInt(elem.text(), 10) - 1);
            }
        },
    });
    // Comments posting
    var comment_area = jQuery('#comments-and-links textarea');
    if(comment_area.val() == '')
        jQuery('#comments-and-links button').hide();
    comment_area
        .focus(function() { jQuery('#comments-and-links button').show() })
        .blur(function() { if(jQuery(this).val() == '') jQuery('#comments-and-links button').hide() });
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

    /*jQuery('.dialog .buttons>.ok').live('click', function(e) {
        // FIXME: Remove shade and stuff
        jQuery(this).closest('.dialog').remove();
    });
    */

    jQuery('a.follow:not(a.open-dialog), a.unfollow:not(a.open-dialog)').live('click', function(event) {
        $this = $(this);
        $parent = $this.parent();
        $.post($this.attr('href'), function(response) {
            if($parent.is('.following')) {
                jQuery('.following a[href=' + $this.attr('href') + ']').parent().removeClass('following').addClass('not_following');
                $parent.removeClass('following').addClass('not_following');
            } else {
                jQuery('.not_following a[href=' + $this.attr('href') + ']').parent().removeClass('not_following').addClass('following');
                $parent.removeClass('not_following').addClass('following');
            }
        });
        return false;
    })
    .hover(function() {
        $this = $(this);
        $this.text($this.attr("data-hover-text"));
    }, function() {
        $this = $(this);
        $this.text($this.attr("data-original-text"));
    });

    // Send proper CSRF token in all ajax request
    $('html').ajaxSend(function(event, xhr, settings) {
        function getCookie(name) {
            var cookieValue = null;
            if (document.cookie && document.cookie != '') {
                var cookies = document.cookie.split(';');
                for (var i = 0; i < cookies.length; i++) {
                    var cookie = jQuery.trim(cookies[i]);
                    // Does this cookie string begin with the name we want?
                    if (cookie.substring(0, name.length + 1) == (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
        if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
            // Only send the token to relative URLs i.e. locally.
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    });

    jQuery('#nav-main a, #footer a').click(function(event) {
        var target = $(this).attr('href');
        if(target.indexOf('/browse/?') >= 0) {
            event.preventDefault();
            window.location = target.replace('?', '#');
        }
    });

    // Sort categories in client, this is a solution to the problem where the category tree is only sorted for one language.
    function sort_lexical(a, b) {
        return jQuery('a', a).text() > jQuery('a', b).text() ? 1 : -1;
    }
    jQuery('ul.level-0 > li').sort(sort_lexical).appendTo('ul.level-0').find('ul.level-1').each(function(index, level_one) {
        jQuery('> li', level_one).sort(sort_lexical).appendTo(level_one).find('ul.level-2').each(function(index, level_two) {
            jQuery('> li', level_two).sort(sort_lexical).appendTo(level_two);
        });
    });

    // Profile image
    var hover_edit_button = true;
    jQuery('#profile-image').hover(
        function() { if (hover_edit_button) $('button.edit', this).show() },
        function() { if (hover_edit_button) $('button.edit', this).hide() }
    );
    jQuery('#profile-image button.edit').click(function() {
        jQuery('#profile-image button.cancel-edit').show();
        jQuery(this).hide().siblings('form').show();
        hover_edit_button = false;
        return false;
    });
    jQuery('#profile-image button.cancel-edit').click(function() {
        jQuery('#profile-image button.edit').show();
        jQuery(this).hide().siblings('form').hide();
        hover_edit_button = true;
        return false;
    });
    jQuery('#profile-image input[type=file]').change(function(e) {
        jQuery('button[type=submit]', jQuery(this).closest('ul')).show();
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
        offset: [15, 0]
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
        jQuery('#cancel-search').hide();
    },
    show: function() {
        // Shows search result dialog
        jQuery('#search-result').fadeIn('fast');
        jQuery('#search').addClass('expanded');
        jQuery('#cancel-search').show();
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
    search: function(callback) {
        // Preforms a search

        var s = jQuery('#search > input').val();
        if(s.length == 0)
            return;

        ApparelSearch.clear();

        ApparelSearch._doSearch({
            model: 'product',
            query: {
                'q': s,
                'limit': 8
            },
            selector: '#search-result-products',
            text: {
                header_plural: 'Found %(count)s products',
                header_singular: 'Found %(count)s product',
                button_plural: 'Show all %(count)s products',
                button_singular: 'Show %(count)s product'
            }
        });

        ApparelSearch._doSearch({
            model: 'look',
            query: {
                'q': s,
                'limit': 6
            },
            selector: '#search-result-looks',
            text: {
                header_plural: 'Found %(count)s looks',
                header_singular: 'Found %(count)s look',
                button_plural: 'Show all %(count)s looks',
                button_singular: 'Show %(count)s look'
            }
        });

        ApparelSearch._doSearch({
            model: 'manufacturer',
            query: {
                'q': s,
                'limit': 10
            },
            selector: '#search-result-manufacturers',
            text: {
                header_plural: 'Found %(count)s matching brands',
                header_singular: 'Found %(count)s matching brand',
                button_plural: 'Show all %(count)s matching brands',
                button_singular: 'Show %(count)s matching brand'
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
            url: '/search/' + opts.model,
            dataType: 'json',
            data: opts.query,
            complete: function(request, status) {
                console.log('Do cleanup here (hide "now searching" visual clue and whatever)')
            },
            success: function(response, status, request) {
                if(!response) return;
                var list = jQuery(opts.selector);
                jQuery.each(response.object_list, function(i, object) {
                    var root;
                    if(opts.model == 'product') {
                        root = list;
                    } else {
                        root = jQuery('<li/>').appendTo(list);
                    }
                    root.append(object)

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
                            opts.text.header_singular,
                            opts.text.header_plural,
                            response.paginator.count
                        ),
                        { count: response.paginator.count },
                        true
                    )
                );

                jQuery('a.' + opts.selector.substring(1)).text(
                    interpolate(
                        ngettext(
                            opts.text.button_singular,
                            opts.text.button_plural,
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
        ngettext('Show %(count)s product', 'Show all %(count)s products', 0);
        ngettext('Show %(count)s look', 'Show all %(count)s looks', 0);
        ngettext('Show %(count)s matching brand', 'Show all %(count)s matching brands', 0);
        ngettext('%s product', '%s products', 0);
    },

    format_query: function(query) {
        // Takes a query as an object and stringifies if after removing the
        // size-property

        if('limit' in query)
            delete(query['limit']);

        var pairs = [];
        for(var key in query) {
            pairs.push(
               encodeURIComponent(key)
                + '='
                + encodeURIComponent(query[key])
            );
        }

        return pairs.join('&')
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

    jQuery('#cancel-search').click(function(e) {
        ApparelSearch.cancel();
        return false;
    });

    jQuery('#search-result-manufacturers a').live('click', function(e) {
        ApparelSearch.cancel();
        location.href = jQuery(this).attr('href');
    });

    jQuery('#search-result .search-result-products').click(function(e) {
        return search_link_action('search-result-products');
    });

    jQuery('#search-result .search-result-looks').click(function(e) {
        return search_link_action('search-result-looks');
    });

    jQuery('#search-result .search-result-manufacturers').click(function(e) {
        return search_link_action('search-result-manufacturers');
    });

    function search_link_action(type) {
        var query = jQuery('#' + type).data('last-query');

        switch(type) {
            case 'search-result-products':
                if(!query) {
                    console.error('Could not find search query');
                    break;
                }

                location.href = '/browse/#' + ApparelSearch.format_query(query);
                break;

            case 'search-result-looks':
                if(!query) {
                    console.error('Could not find search query');
                    break;
                }

                location.href = '/looks/?' + ApparelSearch.format_query(query);
                break;

            case 'search-result-manufacturers':

                var s = query.q;
                location.href =
                    '/browse/?criterion=manufacturer&'
                    + encodeURIComponent('1:m.name:icontains')
                    + '=' + encodeURIComponent(s)
                    + '&defaults=manufacturer-dialog'
                    + '&defaults='
                    + encodeURIComponent('manufacturer-dialog-filter|' + s)

                break;

            default:
                console.log('No action for %s', type);
        }

        ApparelSearch.cancel();

        // From reset click handler in browse.js
        jQuery('.selected').removeClass('selected');
        jQuery('#product-category .level-1, #product-category .level-2').hide();
        //jQuery('#product-manufacturers .reset').click();
        jQuery('#product-gender li:first > a').addClass('selected');

        return false;
    }
} );
