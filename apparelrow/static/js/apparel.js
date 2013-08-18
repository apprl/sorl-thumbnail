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

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

var csrftoken = getCookie('csrftoken');

$.ajaxSetup({
    crossDomain: false, // obviates need for sameOrigin test
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type)) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

function increase_counts(counts, new_count) {
    // For each element, set to new_count if available, otherwise increase the current count with 1
    counts.each(function() {
        $(this)
            .hide()
            .html(typeof new_count != "undefined" ? new_count : parseInt($(this).html()) + 1)
            .fadeIn();
    });
}

/**
 * Creates a modal dialog with yes/no as alternatives.
 */
window.create_modal_dialog = function(header, messages, yes_action, no_action) {
    // TODO: replace this on looks and look_detail
};

$(document).ready(function() {
    // Define an empty console.log if it's not available
    if(!'console' in window)
        window.console = { log: function() {} };

    // Language dropdown submit form
    $(document).on('click', '#language-dropdown li', function() {
        $('#languageform select').val($('a', this).data('language'));
        $('#languageform').submit();
        return false;
    });

    // Track custom events
    function trackEvent(category, action) {
        return function() {
            var el = $(this),
                sid = el.attr('data-sid'),
                slug = el.attr('data-slug'),
                vendor = el.attr('data-vendor'),
                price = parseInt(el.attr('data-price'), 10);

            _gaq.push(['_trackEvent', category, action, vendor + ' - ' + slug, price]);

            return true;
        }
    }

    function trackInviteEvent(category) {
        return function() {
            _gaq.push(['_trackEvent', category, 'InviteFriends']);

            return true;
        }
    }

    // Track buy clicks
    $(document).on('click', '#search-result a.btn-buy', trackEvent('Search', 'BuyReferral'))
               .on('click', 'body.product .product-info a.btn-buy', trackEvent('Product', 'BuyReferral'))
               .on('click', 'body.page-shop #content a.btn-buy', trackEvent('Shop', 'BuyReferral'))
               .on('click', 'body.profile #content a.btn-buy', trackEvent('Profile', 'BuyReferral'))
               .on('click', 'body.feed #content a.btn-buy', trackEvent('Feed', 'BuyReferral'))
               .on('click', '.tooltip a.btn-buy', trackEvent('Look', 'BuyReferral'));

    // Track likes
    $(document).on('click', 'body.product .btn-product-like', trackEvent('Product', 'ProductLike'))
               .on('click', 'body.shop .btn-product-like', trackEvent('Shop', 'ProductLike'))
               .on('click', 'body.profile .btn-product-like', trackEvent('Profile', 'ProductLike'));

    // Track invites
    $(document).on('click', '#nav-user .facebook-invite', trackInviteEvent('Menu'))
               .on('click', 'body.feed .sidebar .facebook-invite', trackInviteEvent('Profile'))
               .on('click', 'body.profiles #body-header .facebook-invite', trackInviteEvent('Members'))
               .on('click', 'body.profile-login-flow #content .facebook-invite', trackInviteEvent('Welcome'))
               .on('click', '#footer .facebook-invite', trackInviteEvent('Footer'));


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
                var newComment = jQuery(jQuery.parseHTML(response)).find('.comments-list li').last()
                newComment.appendTo(form.siblings('.comments-list')).slideDown('fast');
                increase_counts(jQuery('a.comments > span.count'));
            }
        };
        jQuery.ajax(params);
        return false;
    });

    // Show follow button over avatar lager follow element
    jQuery(document).on('mouseenter', '.avatar-large-follow', function(event) {
        jQuery(this).find('.follow-container').show();
    }).on('mouseleave', '.avatar-large-follow', function(event) {
        jQuery(this).find('.follow-container').hide();
    });

    // New follow button, uses only a single element
    jQuery(document).on('click', '.btn-follow, .btn-unfollow', function(event) {
        var element = jQuery(this);
        if(element.hasClass('btn-follow')) {
            jQuery.post(element.data('follow-url'), function(data) {
                element.removeClass('btn-follow').addClass('btn-unfollow').text(element.data('unfollow-text')).removeClass('btn-success');
                if(share_settings['follow_profile'] === false) {
                    ApparelActivity.notification('follow', element.data('profile-type'), element.data('profile-id'));
                }
            });
        } else {
            jQuery.post(element.data('unfollow-url'), function(data) {
                element.removeClass('btn-unfollow').addClass('btn-follow').text(element.data('follow-text')).removeClass('btn-default btn-danger').addClass('btn-success');
            });
        }
        return false;
    }).on('mouseenter', '.btn-unfollow', function(event) {
        jQuery(this).text(jQuery(this).data('unfollow-hover')).addClass('btn-danger').removeClass('btn-default');
    }).on('mouseleave', '.btn-unfollow', function(event) {
        jQuery(this).text(jQuery(this).data('unfollow-text')).removeClass('btn-danger').addClass('btn-default');
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

    // Profile image and about inline form
    var hover_edit_button = true;
    var $profileImage = $('#profile-image');
    if(!$profileImage.hasClass('no-hover')) {
        $profileImage.hover(
            function() { if (hover_edit_button) $('.btn-edit', this).show() },
            function() { if (hover_edit_button) $('.btn-edit', this).hide() }
        );
    } else {
        $profileImage.find('.btn-edit').show();
    }
    $('#profile-image .btn-edit').click(function() {
        $('#profile-about form, #profile-about .btn-cancel').hide();
        $('#profile-about .description').show();
        hover_about_edit = true;
        $('#profile-image .btn-cancel').show();
        $(this).hide().siblings('form').show();
        hover_edit_button = false;
        return false;
    });
    $('#profile-image .btn-cancel').click(function() {
        $('#profile-image .btn-edit').show();
        $(this).hide().siblings('form').hide();
        hover_edit_button = true;
        return false;
    });

    // Look-like and hotspots
    if (!is_mobile()) {
        $('.look-medium .hotspot, .look-large .hotspot').hide();
        // Hide hotspots and look-like on new data from infinite scroll plugin
        $(document).on('infinite_scroll_data', function(e) {
            $('.look-medium .hotspot, .look-large .hotspot').hide();
        });
        // Look medium and large hotspot hover
        $(document).on('mouseenter', '.look-medium, .look-large', function() { $('.hotspot', this).show(); })
                   .on('mouseleave', '.look-medium, .look-large', function() { $('.hotspot').hide(); });
    } else {
        $(document).on('infinite_scroll_data', function(e) {
            $('.hotspot').show();
        });
        $('.hotspot').show();
    }

    // Enable tooltip for large and medium looks
    jQuery().enableApprlTooltip('.look-large .product');

    // Product like - show tooltip if no previously likes
    // TODO: fix later
    //jQuery(document).on('mousenter', '.btn-product-like', function() {
        //if(hasLiked == false) {
            //var element = jQuery(this);
            //if(element.children().length == 0) {
                //element.append('<a href="#" class="product-heart-tooltip"><span>' + gettext('Like products to save it to your profile and get sale alerts') + '</span></a>');
            //} else {
                //element.children().show();
            //}
        //}
    //}).on('mouseleave', '.btn-product-like', function() {
        //jQuery(this).children().hide();
    //});

    // Click on like buttons
    $(document).on('click', '.btn-product-like', {type: 'product'}, ApparelActivity.like_handler)
               .on('click', '.btn-look-like', {type: 'look'}, ApparelActivity.like_handler);

    // Update likes count
    // TODO: still in use? does it work?
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

    // Product hover, works with medium
    $(document).on('mouseenter', '.product-medium', function() {
        var element = $(this);
        var product_id = getElementId(element);
        if(!element.data('load_data')) {
            element.find('.buy').text(gettext('Buy'));
            like_element = element.find('.btn-product-like');
            $.getJSON(product_popup_url + '?id=' + product_id, function(json) {
                if(json[0].liked == true) {
                    likeElement(like_element);
                } else {
                    unlikeElement(like_element);
                }
                // TODO: might display comments / likes later
                //if(json[0].likes > 0) {
                    //element.find('.likes').show().text(json[0].likes);
                //} else {
                    //element.find('.likes').hide();
                //}
                //if(json[0].comments > 0) {
                    //element.find('.comments').show().text(json[0].comments);
                //} else {
                    //element.find('.comments').hide();
                //}
            });
        }
        element.data('load_data', true);
        element.find('.hover').show();
        element.find('.product-image').css({opacity: 0.3});
    }).on('mouseleave', '.product-medium', function() {
        $(this).css({opacity: 1}).find('.hover').hide();
        $('.product-image').css({opacity: 1});
    });

    // Look hover, works with medium
    $(document).on('mouseenter', '.look-medium', function() {
        var element = $(this);
        var look_id = getElementId(element);
        if(!element.data('load_data')) {
            like_element = element.find('.btn-look-like');
            $.getJSON(look_popup_url + '?id=' + look_id, function(json) {
                if(json[0].liked == true) {
                    likeElement(like_element);
                } else {
                    unlikeElement(like_element);
                }
            });
        }
        element.data('load_data', true);
        element.find('.hover').show();
        element.find('.look-image').css({opacity: 0.3});
    }).on('mouseleave', '.look-medium', function() {
        $(this).css({opacity: 1}).find('.hover').hide();
        $('.look-image').css({opacity: 1});
    });

    ApparelActivity.setup_share();

    // Back to top
    // TODO: renable later
	//$("#back-top").hide();
	//$(function () {
		//$(window).scroll(function () {
			//if ($(this).scrollTop() > 1500) {
				//$('#back-top').fadeIn();
			//} else {
				//$('#back-top').fadeOut();
			//}
		//});
		//$('#back-top a').click(function () {
			//$('body,html').animate({
				//scrollTop: 0
			//}, 400);
			//return false;
		//});
	//});


    // Facebook invite
    $('.facebook-invite').on('click', function(event) {
        FB.ui({method: 'apprequests', message: 'I think you should try Apprl! All the best stores in one place and you can follow friends, bloggers & brands.', filters: ['app_non_users']});
        event.preventDefault();
    });
});

function getElementId(element, numeric) {
    if(numeric) {
        return parseInt(jQuery(element).attr('id').split('-').pop(), 10);
    }
    return jQuery(element).attr('id').split('-').pop()
}

function likeElement($element) {
    $element.addClass('liked').text($element.data('unlike-text'));
}

function unlikeElement($element) {
    $element.removeClass('liked').text($element.data('like-text'));
}

/**
 * Activity functionality
 */

ApparelActivity = {
    /**
     * Like handler for products and looks
     *
     * Required data attributes: unlike-url, like-url, slug, id
     */
    like_handler: function(event) {
        if(isAuthenticated == false) {
            $('#modal_like_' + event.data.type).modal();
        } else {
            var element = $(this);
            if(element.hasClass('liked')) {
                unlikeElement(element);
                $.post(element.data('unlike-url'), function(data) {
                    if(data && data['success'] == true) {
                        $(document).trigger('unlike', [element, event.data.type, element.data('id')]);
                        unlikeElement(element);

                        // Try to remove from facebook
                        //var data = {'object_type': element.data('type'), 'object_url': element.data('url'), 'action': element.data('action')}
                        //jQuery.post('/facebook/pull/', data, function(response) {
                            //if(response && response['success'] == true) { }
                        //});
                    } else {
                        likeElement(element);
                    }
                });
            } else {
                likeElement(element);
                $.post(element.data('like-url'), function(data) {
                    if(data['success'] == true) {
                        $(document).trigger('like', [element, event.data.type, element.data('id')]);
                        likeElement(element);
                        element.addClass('liked');
                        element.text(element.data('unlike-text'));

                        // Push likes to google analytics
                        _gaq.push(['_trackEvent', event.data.type.capitalize(), 'Like', element.data('slug')]);

                        // Notify user about like
                        if(share_settings['like_' + event.data.type] === false) {
                            ApparelActivity.notification('like', event.data.type, element.data('id'));
                        }
                    } else {
                        unlikeElement(element);
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
                    trackShare(element.data());
                } else if(response && response['success'] == false) {
                    element.parent().html(response['error']).addClass('error');
                }
            }).error(function() {
                sticky.sticky('close');
            });

            return false;
        });

        function trackShare(data) {
            var category = data.type;

            if(category === 'object') {
                category = data.autoShare.split('_').pop();
            }

            _gaq.push(['_trackEvent', category, 'FB ' + data.action, data.url]);
        }
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
        //updateHash('!s', '', true);
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

        $('#search-query').text(s);

        //updateHash('!s', s, false);

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
                'limit': 20
            },
            selector: '#search-result-manufacturers',
            text: {
                header_plural: 'Found %(count)s matching brands',
                header_singular: 'Found %(count)s matching brand',
                button_plural: 'Show all %(count)s matching brands',
                button_singular: 'Show %(count)s matching brand'
            }
        });

        ApparelSearch._doSearch({
            model: 'store',
            query: {
                'q': s,
                'limit': 10
            },
            selector: '#search-result-stores',
            text: {
                header_plural: 'Found %(count)s matching stores',
                header_singular: 'Found %(count)s matching store',
                button_plural: 'Show all %(count)s matching stores',
                button_singular: 'Show %(count)s matching store'
            }
        });

        ApparelSearch._doSearch({
            model: 'user',
            query: {
                'q': s,
                'limit': 10
            },
            selector: '#search-result-profiles',
            text: {
                header_plural: 'Found %(count)s matching members',
                header_singular: 'Found %(count)s matching member',
                button_plural: 'Show all %(count)s matching members',
                button_singular: 'Show %(count)s matching member'
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
                    var $object = jQuery($.parseHTML(object));
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

                var h2 = jQuery('h2.' + opts.selector.substring(1)).text(
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
                ).hide();

                if(response.paginator.count > opts.query['limit']) {
                    abutton.show();
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
        ngettext('Found %(count)s matching member', 'Found %(count)s matching members', 0);
        ngettext('Found %(count)s matching store', 'Found %(count)s matching stores', 0);
        ngettext('Show %(count)s product', 'Show all %(count)s products', 0);
        ngettext('Show %(count)s look', 'Show all %(count)s looks', 0);
        ngettext('Show %(count)s matching brand', 'Show all %(count)s matching brands', 0);
        ngettext('Show %(count)s matching member', 'Show all %(count)s matching members', 0);
        ngettext('Show %(count)s matching store', 'Show all %(count)s matching stores', 0);
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
                if ($('.navbar-toggle').is(':visible')) {
                    $('.navbar-responsive-collapse').collapse('hide');
                }
                return false;
            case 27: // escape
                ApparelSearch.cancel();
                return false;

            default:
                j.data('tid', setTimeout(ApparelSearch.search, 1000));
        }
    });

    /**
     * Disable search hash change
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
    */

    jQuery('#cancel-search').click(function(e) {
        ApparelSearch.cancel();
        return false;
    });

    $('#search-result').on('click', '.search-result-products:not(.disabled)', function(e) {
            return search_link_action('search-result-products');
        }).on('click', '.search-result-looks:not(.disabled)', function(e) {
            return search_link_action('search-result-looks');
        }).on('click', '.search-result-manufacturers:not(.disabled)', function(e) {
            return search_link_action('search-result-manufacturers');
        });

    $(document).on('click', '#search-result #search-result-stores li a', function(e) {
        if(window.location.pathname.slice(0, 5) == '/shop') {
            ApparelSearch.cancel();
        }
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

    var $body = $('body'),
        $pagination = $('.pagination');

    // Set up infinite scroll on all pages with pagination except shop,
    // which has it's own pagination logic
    if($pagination.length && !$body.hasClass('shop') && !$body.hasClass('profile-likes')) {
        var $container = $pagination.prev();

        var last_link = null;
        function getPage(link, callback) {
            if(link.attr('href') != last_link) {
                last_link = link.attr('href');
                $.get(last_link, function(data, statusText, xhr) {
                    var $data = $($.parseHTML(data)),
                        newPagination = $data.filter('.pagination'),
                        content = newPagination.prev();

                    $container.append(content.html());
                    $pagination.html(newPagination.html());

                    $(document).trigger('infinite_scroll_data', [content]);

                    if('function' == typeof callback) callback();
                });
            }
        }

        // Fetch via ajax on pagination clicks
        $pagination.on('click', '.btn-pagination', function() {
            // Keep fetching automatically after the first click
            var $this = $(this);
            $this.addClass('disabled hover').find('span').text($this.data('loading-text'));

            $(window).data('dont-scroll', false);

            getPage($this);
            return false;
        });

        // Set up infinite scroll
        infiniteScroll(function(callback) {
            var link = $pagination.find('.btn-pagination');

            if(link.length)
                getPage(link, callback);
            else
                callback();
        });
    }
});
