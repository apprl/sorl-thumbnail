String.prototype.capitalize = function() {
    return this.charAt(0).toUpperCase() + this.slice(1);
}

/*
    Load detail click earning details for clicks in a modal
 */
function load_detailed_data_clicks(jsonDetail, date, vendor, currency, isStore){
    var html = "<table>";
    for (i = 0; i < jsonDetail.length; i++){
        html += "<tr>" +
                "<td><a href=\""+jsonDetail[i].product_url+"\">" + jsonDetail[i].product_name + "</a></td>" +
                "<td class='center'>"  + jsonDetail[i].clicks + "</td>"
        if (!isStore){
            html += "<td class='center'>" + currency + " " + jsonDetail[i].product_earning.toFixed(2) + "</td>";
        }
        html += "<tr>";
    }
    html += "</table>";
    $("#content-clicks").html(html);
    $("#modal-date").html(date);
    $("#modal-vendor").html(vendor);
    $("#modal_detail_clicks").modal("show");
}

/*
    Returns cookie value given the cookie name
 */
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

/*
    Sets a value and expiration date for a cookie given the cookie name
 */
function setCookie(cname, cvalue, exdays) {
    var d = new Date();
    d.setTime(d.getTime() + (exdays*24*60*60*1000));
    var expires = "expires="+d.toUTCString();
    document.cookie = cname + "=" + cvalue + "; " + expires;
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


$(document).ready(function() {
    // Define an empty console.log if it's not available
    if(!'console' in window)
        window.console = { log: function() {} };

    // Track custom events
    function trackEvent(category, action) {
        return function() {
            var el = $(this);
            if (!el.hasClass('liked')) {
                var sid = el.attr('data-sid'),
                    slug = el.attr('data-slug'),
                    vendor = el.attr('data-vendor'),
                    price = parseInt(el.attr('data-price'), 10);

                ga('send', 'event', category, action, vendor + ' - ' + slug, price);
                _gaq.push(['_trackEvent', category, action, vendor + ' - ' + slug, price]);
            }

            return true;
        }
    }

    function trackLookLikeEvent(category) {
        return function() {
            var el = $(this);
            if (!el.hasClass('liked')) {
                var slug = el.data('slug');

                ga('send', 'event', category, 'LookLike', slug);
                _gaq.push(['_trackEvent', category, 'LookLike', slug]);
            }

            return true;
        }
    }

    function trackInviteEvent(category) {
        return function() {
            ga('send', 'event', category, 'InviteFriends');
            _gaq.push(['_trackEvent', category, 'InviteFriends']);

            return true;
        }
    }

    function trackEmbed(category, action) {
        return function() {
            var slug = $(this).data('slug');

            ga('send', 'event', category, action, slug);
            _gaq.push(['_trackEvent', category, action, slug]);

            return true;
        }
    }

    function trackSignup(category, action) {
        return function() {
            ga('send', 'event', category, action);
            _gaq.push(['_trackEvent', category, action]);

            return true;
        }
    }

    // Track likes
    $(document).on('click', 'body.product-detail-page .btn-product-like', trackEvent('Product', 'ProductLike'))
               .on('click', 'body.shop .btn-product-like', trackEvent('Shop', 'ProductLike'))
               .on('click', 'body.profile-page .btn-product-like', trackEvent('Profile', 'ProductLike'))
               .on('click', 'body.search-page .btn-product-like', trackEvent('Search', 'ProductLike'))
               .on('click', 'body.index .btn-product-like, body.feed-list-page .btn-product-like', trackEvent('Feed', 'ProductLike'));

    $(document).on('click', 'body.look-detail-page .btn-look-like', trackLookLikeEvent('Look'))
               .on('click', 'body.look-list-page .btn-look-like', trackLookLikeEvent('Looks'))
               .on('click', 'body.profile-page .btn-look-like', trackLookLikeEvent('Profile'))
               .on('click', 'body.search-page .btn-look-like', trackLookLikeEvent('Search'))
               .on('click', 'body.index .btn-look-like, body.feed-list-page .btn-look-like', trackLookLikeEvent('Feed'));

    // Track invites
    $(document).on('click', '.navbar .facebook-invite', trackInviteEvent('Menu'));

    // Track embed and short link
    $(document).on('click', 'body.look-detail-page .btn-embed', trackEmbed('Look', 'ClickEmbedButton'))
               .on('click', '#modal_embed_look .modal-body .btn', trackEmbed('Look', 'GetEmbedCode'))
               .on('click', 'body.profile-page .btn-create-shop', trackEmbed('Shop', 'ClickEmbedButton'))
               .on('click', '#modal_embed_shop .modal-body .btn', trackEmbed('Shop', 'GetEmbedCode'))
               .on('click', 'body.product-detail-page .btn-short-link', trackEmbed('Product', 'ClickGetLinkButton'));

    $(document).on('click', '.btn-get-access', trackSignup('Signup', 'ClickSignup'))
               .on('click', '.btn-signup-email', trackSignup('Signup', 'ClickEmailSignup'))
               .on('click', 'body.registration-email .btn-email-signup', trackSignup('Signup', 'ClickEmailSignupSubmit'))
               .on('click', 'body.profile-welcome .btn-login-flow-continue', trackSignup('Signup', 'FollowBrandsPageCompleted'));

    // Set pointer for checkboxes and radiobuttons labels
    $('input[type="checkbox"]').parents().css("cursor", "pointer");
    $('input[type="radio"]').parents().css("cursor", "pointer");

    // Facebook button sign in
    $(document).on('click', '.btn-facebook', function(e) {
        e.preventDefault();

        var el = $(this),
            form = el.parents('form:first');

        if (el.hasClass('btn-facebook-signup')) {
            trackSignup('Signup', 'ClickFacebookSignup');
        } else if (el.hasClass('btn-facebook-login')) {
            trackSignup('Signup', 'ClickFacebookLogin');
        }

        function handleResponse(response){
            if (response.authResponse) {
                $('input[name="access_token"]', form).val(response.authResponse.accessToken);
                $('input[name="uid"]', form).val(response.authResponse.userID);
                form.submit();
            }
        }

        if (isMobileDevice()) {
            window.location = facebook_login_uri;
        } else {
            FB.login(handleResponse, {scope: facebook_scope});
        }
    });


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
                element.removeClass('btn-follow').addClass('btn-unfollow').text(element.data('unfollow-text')).removeClass('btn-success').addClass('btn-default');
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
        $(this).parent().hide();
        hover_edit_button = true;
        return false;
    });

    // Click on like buttons
    $(document).on('click', '.btn-product-like', {type: 'product'}, ApparelActivity.like_handler)
               .on('click', '.btn-look-like', {type: 'look'}, ApparelActivity.like_handler)
               .on('mouseenter', '.btn-look-like, .btn-product-like', ApparelActivity.like_handler_enter)
               .on('mouseleave', '.btn-look-like, .btn-product-like', ApparelActivity.like_handler_leave);

    // Update likes box and adds another badge
    $(document).on('like', function(event, element, type, id) {
        if (typeof userID !== 'undefined' && (!isPartnerUser || type == 'look')) {
            var likes_box = $('#likes-box');
            likes_box.find('> li:first-child').after($('#user_like_template').clone().html());
            if(likes_box.find('> li').length == 1) {
                likes_box.find('> li:first-child').removeClass('hide');
            } else {
                likes_box.find('> li:first-child').addClass('hide');
            }
        }
    });

    $(document).on('unlike', function(event, element, type, id) {
        if (typeof userID !== 'undefined' && (!isPartnerUser || type == 'look')) {
            var likes_box = $('#likes-box');
            likes_box.find('[data-user-id=' + userID + ']').remove();
            if(likes_box.find('> li').length == 1) {
                likes_box.find('> li:first-child').removeClass('hide');
            } else {
                likes_box.find('> li:first-child').addClass('hide');
            }
        }
    });

    $(document).on('mouseenter', '.product-medium-earning', function () {
        $(this).parent().find('.product-medium > .product-image-container').trigger("mouseenter");
    });
    $(document).on('mouseleave', '.product-medium-earning', function () {
        $(this).parent().find('.product-medium > .product-image-container').trigger("mouseleave");
    });
    // Product hover, works with medium
    $(document).on('mouseenter', '.product-medium > .product-image-container', function() {
        var element = $(this),
            product_id = getElementId(element.parent());

        if(!element.data('load_data')) {
            like_element = element.find('.btn-product-like');
            $.getJSON(product_popup_url + '?id=' + product_id, function(json) {
                if(json.length) {
                    if (json[0].liked == true) {
                        likeElement(like_element);
                    } else {
                        unlikeElement(like_element);
                    }
                }
            });
        }
        element.data('load_data', true);
        element.find('.hover').show();
        element.parentsUntil("ul").find('.product-medium-earning').css('visibility', 'visible');
        element.find('.product-image').css({opacity: 0.3});
    }).on('mouseleave', '.product-medium > .product-image-container', function() {
        $(this).find('.hover').hide();
        $('.product-image').css({opacity: 1});
        $(this).parentsUntil("ul").find('.product-medium-earning').css('visibility', 'hidden');
    });

    // Look hover, works with medium
    $(document).on('mouseenter', '.look-medium > .look-image-container', function() {
        var element = $(this),
            look_id = getElementId(element.parent());

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
    }).on('mouseleave', '.look-medium > .look-image-container', function() {
        $(this).find('.hover').hide();
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
        event.preventDefault();
        FB.ui({method: 'apprequests', message: 'I think you should try Apprl! All the best stores in one place and you can follow friends, bloggers & brands.', filters: ['app_non_users']});
        $('.navbar .navbar-responsive-collapse').collapse('hide');
    });

    if (('createTouch' in document)) {
        try {
            var ignore = /:hover/;
            for (var i = 0; i < document.styleSheets.length; i++) {
                var sheet = document.styleSheets[i];
                if (!sheet.cssRules) {
                    continue;
                }
                for (var j = sheet.cssRules.length - 1; j >= 0; j--) {
                    var rule = sheet.cssRules[j];
                    if (rule.type === CSSRule.STYLE_RULE && ignore.test(rule.selectorText)) {
                        if (rule.selectorText.indexOf(',') == -1) {
                            sheet.deleteRule(j);
                        } else {
                            var selectors = rule.selectorText.split(',');
                            for (var k = 0; k < selectors.length; k++) {
                                if (ignore.test(selectors[k])) {
                                    selectors.splice(k, 1);
                                    k--;
                                }
                            }

                            sheet.deleteRule(j);
                            if (selectors.length) {
                                sheet.insertRule(selectors.join(',') + /{.+}/.exec(rule.cssText), j);
                            }
                        }
                    }
                }
            }
        }
        catch (e) {
        }
    }
});

function getElementId(element, numeric) {
    if(numeric) {
        return parseInt(jQuery(element).attr('id').split('-').pop(), 10);
    }
    return jQuery(element).attr('id').split('-').pop()
}

function likeElement($element) {
    $element.addClass('liked').find('span:first').text($element.data('liked-text'));
}

function unlikeElement($element) {
    $element.removeClass('liked').find('span:first').text($element.data('like-text'));
}

function showWarning($element) {
    var slug = $element.attr('data-slug');
    var settings_link = '/profile/settings/email/#location-notifications';
    jQuery.ajax({
        type: 'GET',
        url: '/products/check_location/' + slug + '/',
        success: function(response, status, request) {
            if(response){
                $.notify({
                    message: response + " <a class='alert-warning' style='text-decoration: underline;' href='" + settings_link + "'>Go to location settings</a>"
                }, { // settings
                    type: 'warning',
                    z_index: 10031,
                    offset: 80,
                    delay: 0,
                    placement: {
                        from: "top",
                        align: "center"
                    }
                });
            }
        }
    });
}

/**
 * Activity functionality
 */

ApparelActivity = {
    like_handler_enter: function(event) {
        var element = $(this);
        if (element.hasClass('liked')) {
            element.find('span:first').text(element.data('unlike-text'));
        }
    },

    like_handler_leave: function(event) {
        var element = $(this);
        if (element.hasClass('liked')) {
            element.find('span:first').text(element.data('liked-text'));
        }
    },

    /**
     * Like handler for products and looks
     *
     * Required data attributes: unlike-url, like-url, slug, id
     */
    like_handler: function(event) {
        var element = $(this);
        if(isAuthenticated == false) {
            if(typeof element.attr('data-target') === 'undefined') {
                $('#modal_like_' + event.data.type).modal();
            }
        } else {
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
                // Only show warning if current page is not a product page
                if (typeof element.attr('data-product-page') === 'undefined') {
                    showWarning(element);
                }
                $.post(element.data('like-url'), function(data) {
                    if(data['success'] == true) {
                        $(document).trigger('like', [element, event.data.type, element.data('id')]);
                        likeElement(element);

                        // Push likes to google analytics
                        ga('send', 'event', event.data.type.capitalize(), 'Like', element.data('slug'));
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
        //jQuery('<div>').load('/notification/' + action + '_' + object + '/?id=' + id, function() {
            //jQuery(this).sticky();
        //});
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

            ga('send', 'event', category, 'FB ' + data.action, data.url);
            _gaq.push(['_trackEvent', category, 'FB ' + data.action, data.url]);
        }
    }
}


/**
 *  Search functionality
 */

ApparelSearch = {
    hide: function() {
        // Hides search result dialog
        jQuery('#search-result').hide();
    },
    show: function() {
        // Shows search result dialog
        jQuery('#search-result').show();
    },
    clear: function() {
        // Clears displayed results and cached resultsets and queries
        jQuery('#search-result ul')
            .data('last-query', null)
            .empty();
    },
    cancel: function() {
        // Clears and hides all
        this.hide();
        this.clear();
        jQuery('#search > input').val('');
    },
    search: function(callback, query, gender) {
        // Performs a search
        var s = '';
        if(query) {
            $('#search > input').val(query);
            s = query;
        } else {
            s = $('#search > input').val();
        }

        if(typeof s === 'undefined' || s.length == 0)
            return;

        ApparelSearch.clear();

        // No need to update search query headline anymore because we are
        // reloading the page on search
        //$('#search-query').text(s);

        //updateHash('!s', s, false);

        ApparelSearch._doSearch({
            model: 'product',
            query: {
                'q': s,
                'limit': 3,
                'gender': gender
            },
            selector: '#search-result-products',
        });

        ApparelSearch._doSearch({
            model: 'look',
            query: {
                'q': s,
                'limit': 3,
                'gender': gender
            },
            selector: '#search-result-looks',
        });

        ApparelSearch._doSearch({
            model: 'manufacturer',
            query: {
                'q': s,
                'limit': 20,
                'gender': gender
            },
            selector: '#search-result-manufacturers',
        });

        ApparelSearch._doSearch({
            model: 'store',
            query: {
                'q': s,
                'limit': 10,
                'gender': gender
            },
            selector: '#search-result-stores',
        });

        ApparelSearch._doSearch({
            model: 'user',
            query: {
                'q': s,
                'limit': 30,
                'gender': gender
            },
            selector: '#search-result-profiles',
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
            url: '/backend/search/' + opts.model + '/',
            dataType: 'json',
            data: opts.query,
            complete: function(request, status) {
                // TODO Do cleanup here (hide "now searching" visual clue and whatever)
            },
            success: function(response, status, request) {
                if(!response) return;
                var list = $(opts.selector);
                $.each(response.object_list, function(i, object) {
                    var root;
                    if(opts.model == 'product') {
                        root = list;
                    } else {
                        root = jQuery('<li/>').appendTo(list);
                    }
                    var $object = jQuery($.parseHTML(object));
                    currencyConversion($object.find('.price, .discount-price'));
                    root.append($object);
                });

                var name = opts.model.charAt(0).toUpperCase() + opts.model.slice(1) + ' search';
                ga('send', 'event', 'Search', name, opts.query['q'], response.paginator.count);
                _gaq.push(['_trackEvent', 'Search', name, opts.query['q'], response.paginator.count]);

                var h4 = $('h4.' + opts.selector.substring(1));
                    h4.find('> span').text(response.header_text);
                var h4_a = h4.find('> a');

                var href_attr = '#';
                switch(opts.selector) {
                    case '#search-result-products':
                        href_attr = browse_url + '?' + ApparelSearch.format_query(opts.query);
                        h4_a.attr('href', href_attr);
                        break;

                    case '#search-result-looks':
                        href_attr = looks_search_url + '?' + ApparelSearch.format_query(opts.query);
                        h4_a.attr('href', href_attr);
                        break;
                }

                var abutton = $('a.' + opts.selector.substring(1)).text(response.button_text).attr('href', href_attr).hide();

                if(response.paginator.count > opts.query['limit']) {
                    abutton.show();
                    h4_a.show();
                }

                list.data('last-query', opts.query);
            }
        });
    },

    format_query: function(query) {
        var query_copy = $.extend({}, query);
        // Takes a query as an object and stringifies if after removing the
        // size-property

        if('limit' in query_copy)
            delete(query_copy['limit']);

        var pairs = [];
        for(var key in query_copy) {
            pairs.push(
               encodeURIComponent(key)
                + '='
                + encodeURIComponent(query[key])
            );
        }

        return pairs.join('&')
    }
};

//function getHashParameterByName(name) {
    //name = name.replace(/[\[]/, "\\\[").replace(/[\]]/, "\\\]");
    //var regexS = "[\\?&]?" + name + "=([^&#]*)";
    //var regex = new RegExp(regexS);
    //var results = regex.exec(window.location.hash);
    //if(results == null)
        //return "";
    //else
        //return decodeURIComponent(results[1].replace(/\+/g, " "));
//}

//function updateHash(name, value, remove) {
    //var hash_object = {};
    //var found = false;
    //if(window.location.hash.substring(1)) {
        //jQuery.each(window.location.hash.substring(1).split('&'), function(index, elem) {
            //var pair = elem.split('=');
            //if(pair[0] == name) {
                //pair[1] = value;
                //found = true;
            //}
            //if(!(remove && found)) {
                //if (pair[1]) {
                    //hash_object[pair[0]] = pair[1];
                //}
            //}
        //});
    //}
    //if(!found && !remove) {
        //hash_object[name] = value;
    //}

    //// Use decodeURIComponent because jQuery.param returns it encoded
    //window.location.hash = decodeURIComponent(jQuery.param(hash_object));
//}

// DOM bindings

jQuery(document).ready(function() {
    //jQuery('#search > input').keyup(function(e) {
        //var j = jQuery(this);
        //clearTimeout(j.data('tid'));

        //console.log('heeere');

        //switch(e.keyCode) {
            //case 0: // command+tab
            //case 9: // tab
            //case 17: // ctrl
            //case 18: // alt
            //case 224: // command
                //return false;
            //case 13: // enter
                //ApparelSearch.search();
                //if ($('.navbar-toggle').is(':visible')) {
                    //$('.navbar-responsive-collapse').collapse('hide');
                //}
                //return false;
            //case 27: // escape
                //ApparelSearch.cancel();
                //return false;

            //default:
                //j.data('tid', setTimeout(ApparelSearch.search, 1000));
        //}
    //});

    /**
     * Disable search hash change
     */
    //jQuery(window).bind('hashchange', function() {
        //var hash_query = getHashParameterByName('!s');
        //if(hash_query && ApparelSearch.last_query != hash_query) {
            //ApparelSearch.search(null, hash_query);
        //}
    //});

    //var hash_query = getHashParameterByName('!s');
    //if(hash_query && ApparelSearch.last_query != hash_query) {
        //ApparelSearch.search(null, hash_query);
    //}

    //$('#cancel-search').click(function(e) {
        //ApparelSearch.cancel();
        //return false;
    //});

    //$('#search-result').on('click', '.search-result-products:not(.disabled)', function(e) {
            //return search_link_action('search-result-products');
        //}).on('click', '.search-result-looks:not(.disabled)', function(e) {
            //return search_link_action('search-result-looks');
        //}).on('click', '.search-result-manufacturers:not(.disabled)', function(e) {
            //return search_link_action('search-result-manufacturers');
        //});

    //$(document).on('click', '#search-result #search-result-stores li a', function(e) {
        //if(window.location.pathname.slice(0, 5) == '/shop') {
            //ApparelSearch.cancel();
        //}
    //});

    //function search_link_action(type) {
        //var query = jQuery('#' + type).data('last-query');

        //switch(type) {
            //case 'search-result-products':
                //if(!query) {
                    //console.error('Could not find search query');
                    //break;
                //}

                //window.location.href = browse_url + '?' + ApparelSearch.format_query(query);
                //if(window.location.pathname == browse_url) {
                    //ApparelSearch.cancel();
                    //window.location.reload();
                //}

                //break;

            //case 'search-result-looks':
                //if(!query) {
                    //console.error('Could not find search query');
                    //break;
                //}

                //window.location.href = '/looks/search/?' + ApparelSearch.format_query(query);
                //break;

            //case 'search-result-manufacturers':
                //window.location.href = browse_url + '?brands_filter=' + encodeURIComponent(query.q);
                //break;
        //}

        //return false;
    //}

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

                    $(document).trigger('infinite_scroll_data', [content]);

                    $container.append(content.html());
                    $pagination.html(newPagination.html());

                    if('function' == typeof callback) callback();
                });
            }
        }

        // Fetch via ajax on pagination clicks
        $pagination.on('click', '.btn-pagination', function() {
            // Keep fetching automatically after the first click
            $('#pagination-loader').show();
            var $this = $(this);
            $this.addClass('disabled hover').find('span').text($this.data('loading-text'));

            $(window).data('dont-scroll', false);

            getPage($this);
            $('#pagination-loader').hide();
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