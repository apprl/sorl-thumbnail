String.prototype.capitalize = function() {
    return this.charAt(0).toUpperCase() + this.slice(1);
}

// From http://detectmobilebrowsers.com/
function is_mobile() {
    var ua = navigator.userAgent||navigator.vendor||window.opera;
    if(/android.+mobile|avantgo|bada\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|meego.+mobile|midp|mmp|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\.(browser|link)|vodafone|wap|windows (ce|phone)|xda|xiino/i.test(ua)||/1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\-(n|u)|c55\/|capi|ccwa|cdm\-|cell|chtm|cldc|cmd\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\-s|devi|dica|dmob|do(c|p)o|ds(12|\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\-|_)|g1 u|g560|gene|gf\-5|g\-mo|go(\.w|od)|gr(ad|un)|haie|hcit|hd\-(m|p|t)|hei\-|hi(pt|ta)|hp( i|ip)|hs\-c|ht(c(\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\-(20|go|ma)|i230|iac( |\-|\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\/)|klon|kpt |kwc\-|kyo(c|k)|le(no|xi)|lg( g|\/(k|l|u)|50|54|\-[a-w])|libw|lynx|m1\-w|m3ga|m50\/|ma(te|ui|xo)|mc(01|21|ca)|m\-cr|me(di|rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\-2|po(ck|rt|se)|prox|psio|pt\-g|qa\-a|qc(07|12|21|32|60|\-[2-7]|i\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\-|oo|p\-)|sdk\/|se(c(\-|0|1)|47|mc|nd|ri)|sgh\-|shar|sie(\-|m)|sk\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\-|v\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\-|tdg\-|tel(i|m)|tim\-|t\-mo|to(pl|sh)|ts(70|m\-|m3|m5)|tx\-9|up(\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\-|your|zeto|zte\-/i.test(ua.substr(0,4))) {
          return true;
      }
      return false;
}

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
    var modal_dialog = jQuery('<div class="dialog"></div>').html(
        jQuery('#error_dialog_template').render({
            header: header,
            messages: messages
        })
    ).appendTo('body').overlay({
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
function create_html_dialog(url_to_html, large_dialog, close_callback, width) {
    var dialog = jQuery('<div class="dialog"></div>');

    if(large_dialog) {
        dialog.addClass('large-dialog');
    }

    if(width) {
        dialog.css('width', width + 'px');
    }

    dialog.load(url_to_html).appendTo('body').overlay({
        mask: {
            color: '#000000',
            loadSpeed: 200,
            opacity: 0.5
        },
        load: true,
        closeOnClick: true,
        close: '.close',
        top: 100,
        onClose: function(e) {
            if(close_callback !== undefined && close_callback) {
                close_callback();
            } else {
                this.getTrigger().remove();
            }
        }
    });
}

jQuery(document).ready(function() {
    // Define an empty console.log if it's not available
    if(!'console' in window)
        window.console = { log: function() {} };

    // Make all textareas autogrow
    //jQuery('textarea').autosize();

    // Subnav dropdown code

    var closetimer = false;
    var subnav = false;
    function close(event) {
        if(subnav) {
            subnav.hide();
            subnav.siblings('a').removeClass('suppress-selected');
            subnav = false;
        }
    }
    function timer(event) {
        closetimer = window.setTimeout(function() { close(event) }, 300);
    }
    function cancel(event) {
        if(closetimer) {
            jQuery(this).find('a').addClass('suppress-selected');
            window.clearTimeout(closetimer);
        }
    }
    function open(event) {
        cancel(event);
        var link_handle = jQuery(this).find('a').addClass('suppress-selected');
        var temp_subnav = jQuery(this);
        if(temp_subnav.hasClass('subnav-handle')) {
            temp_subnav = temp_subnav.find('.subnav');
        } else if(temp_subnav.hasClass('subnav-gray-handle')) {
            temp_subnav = temp_subnav.find('.subnav-gray');
        }
        if(temp_subnav && subnav && temp_subnav.attr('id') != subnav.attr('id')) {
            close(event);
        }
        subnav = temp_subnav.show();
    }
    jQuery('.subnav-handle, .subnav-gray-handle').on('mouseenter', open).on('mouseleave', timer);

    // Track custom events

    function trackEvent(category, action) {
        return function() {
            var el = $(this),
                slug = el.attr('data-slug'),
                vendor = el.attr('data-vendor'),
                price = parseInt(el.attr('data-price'), 10);

            _gaq.push(['_trackEvent', category, action, vendor + ' - ' + slug, price]);

            return true;
        }
    }

    // Track buy clicks

    $('body.product a.btn-buy').live('click', trackEvent('Product', 'BuyReferral'));
    $('body.page-shop a.btn-buy').live('click', trackEvent('Shop', 'BuyReferral'));
    $('body.profile a.btn-buy').live('click', trackEvent('Profile', 'BuyReferral'));
    $('body.feed a.btn-buy').live('click', trackEvent('Feed', 'BuyReferral'));
    $('.tooltip a.buy-now').live('click', trackEvent('Look', 'BuyReferral'));

    // Track likes

    $('body.product a.product-like').live('click', trackEvent('Product', 'ProductLike'));
    $('body.page-shop a.product-like').live('click', trackEvent('Shop', 'ProductLike'));
    $('body.profile a.product-like').live('click', trackEvent('Profile', 'ProductLike'));

    // All elements with class open-dialog should open a dialog and load html from href-url
    jQuery('.open-dialog').live('click', function(event) {
        // TODO: replace attr with data when we change to new jquery version
        var width = jQuery(this).attr('data-dialog-width');
        if (width) {
            create_html_dialog(jQuery(this).attr('href'), false, false, width);
        } else {
            create_html_dialog(jQuery(this).attr('href'));
        }
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

    // Comments posting
    var comment_area = jQuery('.comment-box textarea');
    if(comment_area.val() == '')
        jQuery('.comment-box button').hide();
    comment_area
        .focus(function() { jQuery(this).parents('form').find('button').show(); })
        .blur(function() { if(jQuery(this).val() == '') jQuery(this).parents('form').find('button').hide(); });


    jQuery(document).on('submit', '.comment-box form', function(event) {
        var formData = jQuery(this).serializeArray();
        var form = jQuery(this);
        var params = {
            type: this.method,
            url: this.action,
            data: $.param(formData),
            success: function(response, statusText, req) {
                form.find('textarea').val('');
                form.find('button').hide();
                jQuery(response.html).hide().appendTo(form.siblings('.comments-list')).slideDown('fast');
                increase_counts(jQuery('a.comments > span.count'));
            }
        };
        jQuery.ajax(params);
        return false;
    });

    // From: http://www.w3.org/TR/html5/number-state.html#file-upload-state
    function extractFilename(path) {
        var x = path.lastIndexOf('\\');
        if (x >= 0) // Windows-based path
            return path.substr(x+1);
        x = path.lastIndexOf('/');
        if (x >= 0) // Unix-based path
            return path.substr(x+1);
        return path; // just the filename
    }

    jQuery('.upload-field input[type="text"], .upload-field .button').click(function(e) {
        // Forward click events from the fake controls to file object. This doesn't work in FF
        jQuery('input[type=file]', jQuery(this).parent()).focus();
        return false;
    });
    jQuery('.upload-field input[type="file"]').change(function(e) {
        jQuery('input[type="text"]', jQuery(this).closest('.upload-field')).val(extractFilename(this.value));
    });

    // Show follow button over avatar lager follow element
    jQuery(document).on('mouseenter', '.avatar-large-follow', function(event) {
        jQuery(this).find('.follow-container').show();
    }).on('mouseleave', '.avatar-large-follow', function(event) {
        jQuery(this).find('.follow-container').hide();
    });

    // New follow button, uses only a single element
    jQuery(document).on('click', '.btn-follow:not(.open-dialog), .btn-unfollow:not(.open-dialog)', function(event) {
        var element = jQuery(this);
        if(element.hasClass('btn-follow')) {
            jQuery.post(element.data('follow-url'), function(data) {
                element.removeClass('btn-follow').addClass('btn-unfollow').text(element.data('unfollow-text')).removeClass('btn-positive');
                if(share_settings['follow_profile'] === false) {
                    ApparelActivity.notification('follow', element.data('profile-type'), element.data('profile-id'));
                }
            });
        } else {
            jQuery.post(element.data('unfollow-url'), function(data) {
                element.removeClass('btn-unfollow').addClass('btn-follow').text(element.data('follow-text')).removeClass('btn-negative').addClass('btn-positive');
            });
        }
        return false;
    }).on('mouseenter', '.btn-unfollow', function(event) {
        jQuery(this).text(jQuery(this).data('unfollow-hover')).addClass('btn-negative');
    }).on('mouseleave', '.btn-unfollow', function(event) {
        jQuery(this).text(jQuery(this).data('unfollow-text')).removeClass('btn-negative');
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
        if(target.indexOf('/shop/?') >= 0) {
            event.preventDefault();
            window.location = target.replace('?', '#');
        }
    });

    // Sort categories in client, this is a solution to the problem where the category tree is only sorted for one language.
    function sort_lexical(a, b) {
        return jQuery('a', a).attr('data-order') > jQuery('a', b).attr('data-order') ? 1 : -1;
    }
    jQuery('ul.level-0 > li').sort(sort_lexical).appendTo('ul.level-0').find('ul.level-1').each(function(index, level_one) {
        jQuery('> li', level_one).sort(sort_lexical).appendTo(level_one).find('ul.level-2').each(function(index, level_two) {
            jQuery('> li', level_two).sort(sort_lexical).appendTo(level_two);
        });
    });

    // Profile image
    var hover_edit_button = true;
    jQuery('#profile-image').hover(
        function() { if (hover_edit_button) $('.btn-edit', this).show() },
        function() { if (hover_edit_button) $('.btn-edit', this).hide() }
    );
    jQuery('#profile-image .btn-edit').click(function() {
        jQuery('#profile-image .btn-cancel').show();
        jQuery(this).hide().siblings('form').show();
        hover_edit_button = false;
        return false;
    });
    jQuery('#profile-image .btn-cancel').click(function() {
        jQuery('#profile-image .btn-edit').show();
        jQuery(this).hide().siblings('form').hide();
        hover_edit_button = true;
        return false;
    });
    //jQuery('#profile-image input[type="file"]').change(function(e) {
        //jQuery('button[type="submit"]', jQuery(this).closest('ul')).show();
    //});

    // Look-like and hotspots
    if (!is_mobile()) {
        jQuery('.look-medium .look-like, .look-large .look-like, .look-medium .hotspot, .look-large .hotspot').hide();
        // Hide hotspots and look-like on new data from infinite scroll plugin
        jQuery(document).on('infinite_scroll_data', function(e) {
            jQuery('.look-medium .look-like, .look-large .look-like, .look-medium .hotspot, .look-large .hotspot').hide();
        });
        // Look medium and large hover
        jQuery('.look-medium, .look-large').live('mouseenter', function() {
            jQuery('.look-like', this).show();
            jQuery('.hotspot', this).show();
        }).live('mouseleave', function() {
            jQuery('.look-like').hide();
            jQuery('.hotspot').hide();
        });
    } else {
        jQuery(document).on('infinite_scroll_data', function(e) {
            jQuery('.look-like, .hotspot').show();
        });
        jQuery('.look-like, .hotspot').show();
    }

    // Enable tooltip for large and medium looks
    jQuery('.look-large .product, .look-medium .product').enableApprlTooltip();

    // Product like - show tooltip if no previously likes
    jQuery('.product-like').live('mouseenter', function() {
        if(isAuthenticated == true && hasLiked == false) {
            var element = jQuery(this);
            if(element.children().length == 0) {
                element.append('<a href="#" class="product-heart-tooltip"><span>' + gettext('Like a product to save it to your profile') + '</span></a>');
            } else {
                element.children().show();
            }
        }
    }).live('mouseleave', function() {
        jQuery(this).children().hide();
    });

    // Click on like hearts
    jQuery('body').on('click', '.product-like', {type: 'product'}, ApparelActivity.like_handler)
                  .on('click', '.look-like', {type: 'look'}, ApparelActivity.like_handler);

    // Update likes count
    jQuery(document).on('like', function(event, element, type, id) {
      var containers = jQuery('.' + type + '-container[data-id=' + id + ']');
      containers.find('.heart').addClass('liked');
      ApparelActivity.update_count(containers.find('.likes'), true);
      hasLiked = true;
      ApparelActivity.update_count(jQuery('.stats-box .likes .count'), true);
      var avatar = jQuery('.comment-poster-avatar a').clone();
      jQuery('#likes').prepend(jQuery('<li>').append(avatar));
    });

    jQuery(document).on('unlike', function(event, element, type, id) {
      var containers = jQuery('.' + type + '-container[data-id=' + id + ']');
      containers.find('.heart').removeClass('liked');
      ApparelActivity.update_count(containers.find('.likes'), false);
      ApparelActivity.update_count(jQuery('.stats-box .likes .count'), false);
      var avatar = jQuery('.comment-poster-avatar a');
      jQuery('#likes a[href="' + avatar.attr('href') + '"]').parent().remove();
    });

    // Product hover, works with medium and feed
    jQuery('.product-medium, .product-feed').live('mouseenter', function() {
        var element = jQuery(this);
        if(element.parents('#search-result-products').length == 0) {
            var product_id = getElementId(element);
            if(!element.data('load_data')) {
                element.find('.buy').text(gettext('Buy'));
                jQuery.getJSON(product_popup_url + '?id=' + product_id, function(json) {
                    if(json[0].liked == true) {
                        element.find('.product-like').addClass('liked');
                    }
                    if(json[0].likes > 0) {
                        element.find('.likes').show().text(json[0].likes);
                    } else {
                        element.find('.likes').hide();
                    }
                    if(json[0].comments > 0) {
                        element.find('.comments').show().text(json[0].comments);
                    } else {
                        element.find('.comments').hide();
                    }
                });
            }
            element.data('load_data', true);
            element.find('.hover').show();
            element.find('.product-image').css({opacity: 0.3});
        }
    }).live('mouseleave', function() {
        jQuery(this).css({opacity: 1}).find('.hover').hide();
        jQuery('.product-image').css({opacity: 1});
    });

    ApparelActivity.setup_share();
});

function getElementId(element, numeric) {
    if(numeric) {
        return parseInt(jQuery(element).attr('id').split('-').pop(), 10);
    }
    return jQuery(element).attr('id').split('-').pop()
}

/**
 * Activity functionality
 */

ApparelActivity = {
    /**
     * Like handler for products and looks
     *
     * Required data attributes: unlike-url, like-url, slug, id, (dialog-url)
     */
    like_handler: function(event) {
        if(isAuthenticated == false) {
            create_html_dialog(window['dialog_like_' + event.data.type]);
        } else {
            var element = jQuery(this);
            if(element.hasClass('liked')) {
                jQuery.post(element.data('unlike-url'), function(data) {
                    if(data && data['success'] == true) {
                        jQuery(document).trigger('unlike', [element, event.data.type, element.data('id')]);
                        element.removeClass('liked');

                        // Try to remove from facebook
                        //var data = {'object_type': element.data('type'), 'object_url': element.data('url'), 'action': element.data('action')}
                        //jQuery.post('/facebook/pull/', data, function(response) {
                            //if(response && response['success'] == true) { }
                        //});
                    }
                });
            } else {
                jQuery.post(element.data('like-url'), function(data) {
                    if(data['success'] == true) {
                        jQuery(document).trigger('like', [element, event.data.type, element.data('id')]);
                        element.addClass('liked');

                        // Push likes to google analytics
                        _gaq.push(['_trackEvent', event.data.type.capitalize(), 'Like', element.data('slug')]);

                        // Notify user about like
                        if(share_settings['like_' + event.data.type] === false) {
                            ApparelActivity.notification('like', event.data.type, element.data('id'));
                        }
                    }
                });
            }
        }
        return false;
    },

    /**
     * Increase or decrease like count for element.
     */
    update_count: function(elements, like) {
        elements.each(function(index, element) {
            var element = jQuery(element).show();
            var count = parseInt(element.text(), 10) + (like === true ? 1 : -1);
            element.text(count);
            if(count <= 0) {
                element.hide();
            }
        });
    },

    /**
     * Queue a notification.
     */
    notification: function(action, object, id) {
        jQuery('<div>').load('/notification/' + action + '_' + object + '/?id=' + id, function() {
            jQuery(this).sticky();
        });
    },

    /**
     * Handler for share links, content is shared on facebook.
     *
     * Required data attributes: type, id, url, action
     */
    setup_share: function() {
        jQuery(document).on('click', '.notification-share', function(event) {
            var element = jQuery(this);
            var sticky = element.parents('.sticky');
            var data = {
                'object_type': element.data('type'),
                'object_url': element.data('url'),
                'action': element.data('action')
            }

            if(element.parents('div.sticky-note').find('#save-share').is(':checked')) {
                var auto_share = element.data('auto-share');
                share_settings[auto_share] = true;
                data['auto_share'] = auto_share;
            }

            sticky.sticky('stay');
            jQuery.post('/facebook/share/push/', data).success(function(response) {
                sticky.sticky('extend');
                element.parents('.sticky-note').find('p:last-child').remove();
                if(response && response['success'] == true) {
                    element.parent().html(response['message']);
                } else if(response && response['success'] == false) {
                    element.parent().html(response['error']).addClass('error');
                }
            }).error(function() {
                sticky.sticky('close');
            });

            return false;
        });
    }
}


/**
 *  Search functionality
 */

ApparelSearch = {
    last_query: false,
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
        updateHash('!s', '', true);
        jQuery('#search > input').val('');
    },
    search: function(callback, query) {
        // Preforms a search
        var s = '';
        if(query) {
            jQuery('#search > input').val(query);
            s = query;
        } else {
            s = jQuery('#search > input').val();
        }

        if(s.length == 0)
            return;

        ApparelSearch.clear();
        ApparelSearch.last_query = s;

        updateHash('!s', s, false);

        ApparelSearch._doSearch({
            model: 'product',
            query: {
                'q': s,
                'limit': 12
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
                'limit': 5
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
            type: 'POST',
            url: '/search/' + opts.model + '/',
            dataType: 'json',
            data: opts.query,
            complete: function(request, status) {
                // TODO Do cleanup here (hide "now searching" visual clue and whatever)
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
                    var $object = jQuery(object);
                    currencyConversion($object.find('.price, .discount-price'));
                    root.append($object);

                    var item = list.children(':last');
                    item.addClass((i % 2 == 0) ? 'even' : 'odd');
                    if(i == 0)
                        item.addClass('first');
                    if(i == response.object_list.length - 1)
                        item.addClass('last');

                    if(opts.template == 'product_template' && i % 4 == 3)
                        item.addClass('edge');
                });

                var name = opts.model.charAt(0).toUpperCase() + opts.model.slice(1) + ' search';
                _gaq.push(['_trackEvent', 'Search', name, opts.query['q'], response.paginator.count]);

                var h2 = list.closest('.result-container').children('h2').text(
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

                var abutton = jQuery('a.' + opts.selector.substring(1)).text(
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

                if(response.paginator.count == 0) {
                    h2.addClass('disabled');
                    abutton.addClass('btn-disabled').addClass('disabled');
                } else {
                    h2.removeClass('disabled');
                    abutton.removeClass('btn-disabled').removeClass('disabled');
                }

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
    }
};

function getHashParameterByName(name) {
    name = name.replace(/[\[]/, "\\\[").replace(/[\]]/, "\\\]");
    var regexS = "[\\?&]?" + name + "=([^&#]*)";
    var regex = new RegExp(regexS);
    var results = regex.exec(window.location.hash);
    if(results == null)
        return "";
    else
        return decodeURIComponent(results[1].replace(/\+/g, " "));
}

function updateHash(name, value, remove) {
    var hash_object = {};
    var found = false;
    if(window.location.hash.substring(1)) {
        jQuery.each(window.location.hash.substring(1).split('&'), function(index, elem) {
            var pair = elem.split('=');
            if(pair[0] == name) {
                pair[1] = value;
                found = true;
            }
            if(!(remove && found)) {
                if (pair[1]) {
                    hash_object[pair[0]] = pair[1];
                }
            }
        });
    }
    if(!found && !remove) {
        hash_object[name] = value;
    }

    // Use decodeURIComponent because jQuery.param returns it encoded
    window.location.hash = decodeURIComponent(jQuery.param(hash_object));
}

/**
 * Infinite scroll
 * Automatically scrolls one page
 * To keep auto-scrolling after first page, set $(window).data('dont-scroll', false)
 *
 * To reset, set $(window).data('first-scroll', true)
 * */

function infiniteScroll(callback) {
    var $window = jQuery(window),
        $document = jQuery(document),
        lastOffset = $window.scrollTop(),
        loading = false;

    function bottomDistance() {
        return $document.height() - $window.scrollTop();
    }

    // Keep track of the first auto-scroll
    $window.data('first-scroll', true);

    $window.bind('scroll', function() {
        if($window.data('dont-scroll'))
            return;

        var offset = $window.scrollTop(),
            height = $window.height();

        if(!loading && bottomDistance() < 2 * height && offset > lastOffset) {
            if($window.data('first-scroll')) {
                // Just auto-scroll one page until user clicks "load more"
                $window.data('dont-scroll', true);
                $window.data('first-scroll', false);
            }

            loading = true;
            callback(function() {
                loading = false;
            });
        }

        // Store offset to see scroll direction
        lastOffset = offset;
    });
}

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

    jQuery(window).bind('hashchange', function() {
        var hash_query = getHashParameterByName('!s');
        if(hash_query && ApparelSearch.last_query != hash_query) {
            ApparelSearch.search(null, hash_query);
        }
    });

    var hash_query = getHashParameterByName('!s');
    if(hash_query && ApparelSearch.last_query != hash_query) {
        ApparelSearch.search(null, hash_query);
    }

    jQuery('#cancel-search').click(function(e) {
        ApparelSearch.cancel();
        return false;
    });

    jQuery('#search-result .search-result-products:not(.disabled)').live('click', function(e) {
        return search_link_action('search-result-products');
    });

    jQuery('#search-result .search-result-looks:not(.disabled)').live('click', function(e) {
        return search_link_action('search-result-looks');
    });

    jQuery('#search-result .search-result-manufacturers:not(.disabled)').live('click', function(e) {
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

                window.location.href = browse_url + '#' + ApparelSearch.format_query(query);
                if(window.location.pathname == browse_url) {
                    ApparelSearch.cancel();
                    window.location.reload();
                }

                break;

            case 'search-result-looks':
                if(!query) {
                    console.error('Could not find search query');
                    break;
                }

                window.location.href = '/looks/search/?' + ApparelSearch.format_query(query);
                break;

            case 'search-result-manufacturers':
                window.location.href = browse_url + '?brands_filter=' + encodeURIComponent(query.q);
                break;
        }

        return false;
    }

    var $body = jQuery('body'),
        $pagination = jQuery('.pagination');

    // Set up infinite scroll on all pages with pagination except shop,
    // which has it's own pagination logic
    if($pagination.length && !$body.hasClass('page-shop')) {
        var $container = $pagination.prev();

        var last_link = null;
        function getPage(link, callback) {
            if(link.attr('href') != last_link) {
                last_link = link.attr('href');
                jQuery.get(last_link, function(data, statusText, xhr) {
                    var $data = jQuery(data),
                        newPagination = $data.filter('.pagination'),
                        content = newPagination.prev();

                    $container.append(content.html());
                    $pagination.html(newPagination.html());

                    jQuery(document).trigger('infinite_scroll_data');

                    if('function' == typeof callback) callback();
                });
            }
        }

        // Fetch via ajax on pagination clicks
        $('a.next', $pagination).live('click', function() {
            // Keep fetching automatically after the first click

            $(window).data('dont-scroll', false);

            getPage(jQuery(this));
            return false;
        });

        // Set up infinite scroll
        infiniteScroll(function(callback) {
            var link = $pagination.find('a.next');

            if(link.length)
                getPage(link, callback);
            else
                callback();
        });
    }
});
