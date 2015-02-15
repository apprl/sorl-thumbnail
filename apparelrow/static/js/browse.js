$(document).ready(function() {

    // Expand collapsable panels
    var filter_button = $('#product-filter-button');
    var filter_accordion = $('#product-filter-accordion');
    var filters = filter_accordion.find('.panel-collapse');
    var filters_toggle = filter_accordion.find('.accordion-toggle');

    filter_accordion.collapse({toggle: false});
    filters.collapse({toggle: false});

    if (filter_button.is(':hidden')) {
        filter_accordion.collapse('show');
        filters.collapse('show');
        filters_toggle.removeClass('collapsed');
        filter_button.removeClass('collapsed');
    } else {
        filter_accordion.collapse('hide');
        filters.collapse('hide');
        filters_toggle.addClass('collapsed');
        filter_button.addClass('collapsed');
    }
    $(window).on('resize', function() {
        if (filter_button.is(':hidden')) {
            filter_accordion.collapse('show');
            filters.collapse('show');
            filters_toggle.removeClass('collapsed');
        }
    });

    // Currency conversion
    currencyConversion(jQuery('#product-list').find('.price, .discount-price'));

    // Embedded products
    updateEmbeddedProducts($('#product-list > .product-list'));

    History.Adapter.bind(window, 'statechange', function() { // Note: We are using statechange instead of popstate
        var state = History.getState(); // Note: We are using History.getState() instead of event.state
        doFilter(null, state.cleanUrl);
    });

    // Initially hide level 1 and 2 categories
    $('#product-category .level-1, #product-category .level-2').hide();

    // But show parent and sibling to selected category if there is one
    $('#product-category .selected').each(function(index, element) {
        var element = $(element);
        element.siblings('ul').show();
        element.parents('ul').show();
    });

    // Full reset button
    jQuery(document).on('click', '#reset, .btn-reset', function() {
        // Every selected element is deselected
        jQuery('.product-list-container .selected:not(#option-M, #option-W), .container .selected:not(#option-M, #option-W)').removeClass('selected');

        // Every active element is deactivated
        jQuery('.product-list-container .active, .container .active').removeClass('active');

        // Hide level 1 and 2 categories
        jQuery('#product-category .level-1, #product-category .level-2').hide();

        // Initiate individual reset
        jQuery('#product-filter-accordion .reset').click();

        // Select both genders (only embed and profile)
        if(typeof embed_shop_user_id !== 'undefined' || typeof profile_shop_user_id !== 'undefined') {
            jQuery('#product-gender li > a').removeClass('selected');
            jQuery('#product-gender li:first > a').addClass('selected');
        }

        // Sort by
        $('#product-sort li:nth-child(1) a').addClass('selected');

        // Shop view
        $('.shop-view li:nth-child(1) a').addClass('selected');

        // Call getQuery with empty query and force reset
        filter(getQuery({}, true));

        // Reset autoscrolling
        jQuery(window)
            .data('first-scroll', true)
            .data('dont-scroll', false);

        return false;
    });

    // Individual reset button
    $('#product-filter-accordion .reset').click(function(e) {
        e.preventDefault();

        var accordionGroup = $(this).parents('.panel');
        var accordionInner = accordionGroup.find('.panel-body');

        accordionGroup.removeClass('active');
        accordionInner.find('.selected').removeClass('selected');

        switch(accordionInner.attr('id')) {
            case 'product-category':
                $('#product-category .level-1, #product-category .level-2').hide();

                break;
            case 'product-price':
                // Move slider to min and max
                var slider = $('#price-slider').data('slider');
                    slider.values([slider.option('min'), slider.option('max')]);
                break;

            case 'product-manufacturers':
                $('input[name=brand]').val('').blur();
                $('#selected-manufacturers > li').remove();
                break;
        }

        filter(getQuery());
    });

    // Filter price on form submit but never actually submit the form
    jQuery('#product-price form').submit(function() {
        filter(getQuery());
        return false;
    });

    // Disable form submit when filtering manufacturers
    jQuery('#product-manufacturers form').submit(function() {
        return false;
    });

    if (!!(window.history && history.pushState)) {
        $(document).on('click', '#product-gender a', function(e) {
            var x = $('.navbar-nav-main > li > a[data-shop^="true"]');
            var y = $('.navbar .navbar-form[data-search^="true"]');
            var gender = $(this).data('gender');
            if (gender == 'M') {
                x.attr('href', x.attr('href').replace('women', 'men'));
                y.attr('action', y.attr('action').replace('women', 'men'));
            } else if (gender == 'W') {
                x.attr('href', x.attr('href').replace('men', 'women'));
                y.attr('action', y.attr('action').replace('men', 'women'));
            }
            $('#product-gender a').removeClass('selected');
            var href = $(this).addClass('selected').attr('href');
            filter({}, null, href);
            return false;
        });
    }

    // Click handler for manufacturer option-popup
    jQuery(document).on('click', '#available-manufacturers a', function(e) {
        var element = jQuery(this);
        var selected_manufacturers = jQuery('#selected-manufacturers');
        var id = 'manufacturer-' + getElementId(element);

        if(element.hasClass('selected')) {
            jQuery('#' + id, selected_manufacturers).click(); // selected class is removed in this click handler
        } else {
            element.addClass('selected');
            element.clone().attr('id', id).appendTo(
                jQuery('<li>').prependTo(selected_manufacturers)
            );
            filter(getQuery());
        }

        return false;
    });

    // Click handler for stores
    $(document).on('click', '#available-stores a', function(e) {
        jQuery(this).toggleClass('selected');
        filter(getQuery());
        return false;
    });

    // Click handler for manufacturer search results element
    //jQuery(document).on('click', '#search-result-manufacturers a', function(e) {
        //// Cancel search and reset browse filters
        //ApparelSearch.cancel();
        //jQuery('#reset').click();

        //// Get current element and id
        //var element = jQuery(this);
        //var id = 'manufacturer-' + getElementId(element);

        //// If not previously marked as selected, select it, add it to the
        //// selected list and make sure the manufacturer filter is activated
        //var element_available = jQuery('#available-manufacturer-' + id);
        //if(!element_available.hasClass('selected')) {
            //element_available.addClass('selected');
            //element.clone().attr('id', id).appendTo(jQuery('<li>').prependTo(jQuery('#selected-manufacturers')));
            //filter(getQuery());
        //}
    //});

    // Click handler for list of selected manufacturers
    jQuery(document).on('click', '#selected-manufacturers a', function(e) {
        jQuery('#available-manufacturer-' + getElementId(this)).removeClass('selected');
        jQuery(this).closest('li').remove();
        filter(getQuery());

        return false;
    });

    // Sort by
    $(document).on('click', '#product-sort li a', function(e) {
        $('#product-sort li a').removeClass('selected');
        $(this).addClass('selected');
        filter(getQuery());
        return false;
    });

    // Shop view
    $(document).on('click', '.shop-view li a', function() {
        $('.shop-view li a').removeClass('selected');
        var element = $(this).addClass('selected');
        if (element.data('view') == 'latest') {
            $('#product-sort li a').removeClass('selected');
            $('#product-sort li a[data-sort="lat"]').addClass('selected');
        } else {
            $('#product-sort li a').removeClass('selected');
            $('#product-sort li a[data-sort="pop"]').addClass('selected');
        }
        filter(getQuery());
        return false;
    });

    // Product gender filter (only embed and profile)
    if(typeof embed_shop_user_id !== 'undefined' || typeof profile_shop_user_id !== 'undefined') {
        jQuery('#product-gender li > a').click(function() {
            var element = jQuery(this);
            if(!element.hasClass('selected')) {
                element.addClass('selected');
                element.parent().siblings().find('a').removeClass('selected');
                filter(getQuery());
            }
            return false;
        });
    }

    // Product color filter
    jQuery('#product-color li > a').click(function() {
        if(!jQuery(this).hasClass('filtered')) {
            jQuery(this).toggleClass('selected');
            filter(getQuery());
        }
        return false;
    });

    // Product category filter
    jQuery('#product-category li > a').click(function() {
        filter(getQuery());
        return false;
    });

    // Discount price filter
    jQuery('#product-price #discount-price').click(function() {
        jQuery(this).toggleClass('selected');
        filter(getQuery());
        return false;
    });

    infiniteScroll(function(callback) {
        var page = parsePage($('.pagination .btn-pagination'));
        if (page) {
            fetchPage(page, callback);
        } else {
            callback();
        }
    });

    $(document).on('click', '.pagination a', function(e) {
        var $this = $(this);
        $this.addClass('disabled hover').find('span').text($this.data('loading-text'));
        var page = parsePage($this);
        if (page) {
            fetchPage(page);
        }

        // Set up auto-scrolling
        $(window).data('dont-scroll', false);

        return false;
    });

    jQuery.each(window.location.search.substr(1).split('&'), function(i, e) {
        var pair = e.split('=');
        if(pair[0] != 'brands_filter') {
            return;
        }
        var value = unescape(pair[1]);
        jQuery('#product-manufacturers input[name=brand]').attr('value', value).keyup().focus();
    });
});

/**
 * FETCH PAGE
 *
 * Fetch a new page and call callback when finished.
 */
window.fetchPage = function(page, callback) {
    filter(getQuery({page: page}), function() {
        renderPage.apply(null, arguments);
        callback && callback();
    });
}

/**
 * PARSE PAGE
 *
 * Parse href attribute of element for a page number.
 */
window.parsePage = function(link) {
    var attr_href = link.attr('href');
    if (typeof attr_href !== 'undefined' && attr_href !== false) {
        return parseInt(link.attr('href').split('=')[1], 10);
    }
    return false;
}

/**
 * GET QUERY
 *
 * Create a query object and populate it with selected filters. Also make sure
 * that if there are selected filters, mark that filter category as active.
 */
window.getQuery = function(query, reset) {
    query = query || {}
    reset = typeof(reset) != 'undefined' ? reset : false;

    sort_by = $('#product-sort li a.selected').data('sort');
    if(typeof sort_by !== 'undefined' && sort_by !== null && sort_by != 'pop') {
        query['sort'] = sort_by;
    }

    shop_view = $('.shop-view li a.selected').data('view');
    if(typeof shop_view !== 'undefined' && shop_view !== null && shop_view != 'all') {
        query['view'] = shop_view;
    }

    category_list = getElementIds($('#product-category li > a.selected'));
    if(category_list.length > 0) {
        query['category'] = category_list.join(',');
        $('#product-category').closest('.panel').addClass('active');
    } else {
        $('#product-category').closest('.panel').removeClass('active');
    }

    manufacturer_list = getElementIds($('#selected-manufacturers li > a'));
    if(manufacturer_list.length > 0) {
        query['manufacturer'] = manufacturer_list.join(',');
        $('#product-manufacturers').closest('.panel').addClass('active');
    } else {
        $('#product-manufacturers').closest('.panel').removeClass('active');
    }

    store_list = getElementIds($('#product-stores > ul > li > a.selected'));
    if(store_list.length > 0) {
        query['store'] = store_list.join(',');
        $('#product-stores').closest('.panel').addClass('active');
    } else {
        $('#product-stores').closest('.panel').removeClass('active');
    }

    // Only embed and profile
    if(typeof embed_shop_user_id !== 'undefined' || typeof profile_shop_user_id !== 'undefined') {
        gender_list = getElementIds($('#product-gender li > a.selected'));
        if(gender_list.length > 0 && gender_list[0]) {
            query['gender'] = gender_list[0];
        }
    }

    color_list = getElementIds($('#product-color a.color.selected'));
    if(color_list.length > 0) {
        query['color'] = color_list.join(',');
        $('#product-color').closest('.panel').addClass('active');
    }

    pattern_list = getElementIds($('#product-color a.pattern.selected'));
    if(pattern_list.length > 0) {
        query['pattern'] = pattern_list.join(',');
        $('#product-color').closest('.panel').addClass('active');
    }

    if(color_list.length == 0 && pattern_list.length == 0) {
        $('#product-color').closest('.panel').removeClass('active');
    }

    if($('#price-slider').is('.selected')) {
        query['price'] =
              $("input[name=pricerange_min]").val()
            + ','
            + $("input[name=pricerange_max]").val();
        $('#product-price').closest('.panel').addClass('active');
    }

    if($('#discount-price').is('.selected')) {
        query['discount'] = 1;
        $('#product-price').closest('.panel').addClass('active');
    }

    if(!reset && window.location.search.length > 0) {
        var pairs = window.location.search.substr(1).split('&');
        for(var i = 0; i < pairs.length; i++) {
            keyval = pairs[i].split('=');
            if(keyval[0] == 'q') {
                query['q'] = keyval[1];
            }
            if(keyval[0] == 'f') {
                query['f'] = keyval[1];
            }
        }
    }

    return query;
}

function getElementId(element) {
    var result = false;
    var attr_id = jQuery(element).attr('id');
    if (typeof attr_id !== 'undefined' && attr_id !== false) {
        var attr_id_split = attr_id.split('-');
        if (attr_id_split.length >= 2) {
            result = attr_id_split.pop();
        }
    }

    return result;
}

function getElementIds(elements) {
    return jQuery.map(elements, getElementId);
}

/**
 * Filter by AJAX
 */
function filter(query, callback, path) {
    var queryWithoutPage = $.extend({}, query);
    var page = queryWithoutPage['page'];
    delete queryWithoutPage['page'];
    var querystring = decodeURIComponent($.param(queryWithoutPage, true));
    var pathname = path || window.location.pathname;
    if (!querystring) {
        History.pushState({pushed: true}, null, pathname);
    } else {
        History.pushState({pushed: true}, null, pathname + '?' + querystring);
    }

    if (typeof page !== 'undefined') {
        doFilter(callback, undefined, page);
    }
}

function doFilter(callback, url, page) {

    var callback = callback || renderProducts;
    var page = page || 1;
    if (typeof url !== 'undefined') {
        $.getJSON(url, {page: page}, function(response) {
            updateSelected(response);
            callback(response);
        });
    } else {
        $.getJSON(window.location.pathname + window.location.search, {page: page}, callback);
    }
}

function renderPage(products) {
    var $html = $(products.html);
    var $list = $html.filter('.product-list');
    var $pagination = $html.filter('.pagination');

    currencyConversion($list.find('.price, .discount-price'));
    updateEmbeddedProducts($list);

    $('#product-list > .product-list').append($list.html());
    $('.pagination').html($pagination.html());

    $('#product-list').trigger('post_browse_render');

    if(window.location.search && window.location.search != '?') {
        $('#reset').show()
    } else {
        $('#reset').hide()
    }

    $('#product-list').css('opacity', 1);
}

/**
 * Apply filter on available browse options.
 */
function filterCriteria(criteria_filter) {
    if('manufacturers' in criteria_filter && !jQuery('#product-manufacturers').prev().hasClass('active')) {
        ManufacturerBrowser.reset();

        jQuery.each(criteria_filter['manufacturers'], function(i, manufacturer) {
            ManufacturerBrowser.renderItem(manufacturer);
        });
    }

    if('stores' in criteria_filter && !$('#product-stores').closest('.panel').hasClass('active')) {
        $('#available-stores').html('');
        $.each(criteria_filter['stores'], function(i, store) {
            var $a = $('<a>')
                .attr('href', window.location.pathname + '?store=' + store[0])
                .attr('id', 'available-store-' + store[0])
                .text(store[1]);

            if($('#store-' + store[0]).length > 0)
                $a.addClass('selected');

            $('<li>')
                .append($a)
                .appendTo($('#available-stores'));
        });
    }

    if('categories' in criteria_filter) {
        jQuery('#product-category li > a').each(function(index) {
            var this_element = jQuery(this);
            var this_element_id = parseInt(getElementId(this_element), 10);
            if(this_element_id in criteria_filter['categories']) {
                this_element.parents('.filtered').removeClass('filtered');
            } else {
                this_element.parent().addClass('filtered');
            }
        });
        jQuery('#product-category > li.first').removeClass('first');
        jQuery('#product-category > li:not(.filtered):first').addClass('first');
    }

    if('colors' in criteria_filter) {
        jQuery('#product-color a').each(function(index) {
            var this_element = jQuery(this);
            var this_element_id = parseInt(getElementId(this_element), 10);
            if(jQuery.inArray(this_element_id, criteria_filter['colors']) >= 0) {
                this_element.removeClass('filtered');
            } else {
                this_element.addClass('filtered');
            }
        });
    }

    if('pricerange' in criteria_filter) {
        var min = parseInt(criteria_filter.pricerange.min, 10),
            max = parseInt(criteria_filter.pricerange.max, 10),
            mid = parseInt(min + (max - min) / 2, 10);

        var values = $('#price-slider').slider('values');
        if(values[0] > max)
            values[0] = min;
        if(values[1] < min)
            values[1] = max;
        $('#price-slider').slider('option', 'min', min);
        $('#price-slider').slider('option', 'max', max);
        if (!jQuery('#product-price > a').hasClass('selected')) {
            $('#price-slider').slider('values', criteria_filter.pricerange.selected.split(','));
        } else {
            $('#price-slider').slider('values', values);
        }
    }
}

function updateSelected(products) {
    // Select categories
    $('#product-category a.selected').removeClass('selected');
    if(products.selected_categories && products.selected_categories.length > 0) {
        // If we have a select category
        jQuery.each(products.selected_categories, function(i, id) {
            var category = jQuery('#category-' + id).addClass('selected');
            category.siblings('ul').show();
            category.parents('ul').show();
        });
        jQuery('#product-category').closest('.panel').addClass('active');
    }

    // Select gender
    if(products.selected_gender && products.selected_gender.length > 0) {
        products.selected_gender = products.selected_gender.split();
        $.each(products.selected_gender, function(i, id) {
            $('#option-' + id).addClass('selected');
        });
    } else {
        if(!$('#product-gender li > a').hasClass('selected')) {
            $('#product-gender li:first > a').addClass('selected');
        }
    }

    // Select price
    if(products.selected_price) {
        $('#price-slider').data('slider').values(products.selected_price);
        $('#product-price').closest('.panel').addClass('active');
    }

    // Select discount
    if(products.selected_discount) {
        $('#discount-price').addClass('selected');
    } else {
        $('#discount-price').removeClass('selected');
    }

    // Select colors and patterns
    $('#product-color a.selected').removeClass('selected');
    if(products.selected_colors && products.selected_colors.length > 0) {
        jQuery.each(products.selected_colors, function(i, id) {
            jQuery('#option-' + id).addClass('selected');
        });
        $('#product-color').closest('.panel').addClass('active');
    }
    if(products.selected_patterns && products.selected_patterns.length > 0) {
        jQuery.each(products.selected_patterns, function(i, id) {
            jQuery('#option-' + id).addClass('selected');
        });
        $('#product-color').closest('.panel').addClass('active');
    }

    // Select brands
    $('#selected-manufacturers').html('');
    if(products.selected_brands && products.selected_brands.length > 0) {
        jQuery.each(products.selected_brands, function(i, id) {
            var data = products.selected_brands_data[id];
            jQuery('#available-manufacturer-' + id).addClass('selected');
            jQuery('<li>').append(
                jQuery('<a>').attr({id: 'manufacturer-' + id, href: data['href']}).text(data['name'])
            ).prependTo('#selected-manufacturers');
        });
        $('#product-manufacturers').closest('.panel').addClass('active');
    }

    // Select store
    $('#product-stores a.selected').removeClass('selected');
    if(products.selected_stores && products.selected_stores.length > 0) {
        jQuery.each(products.selected_stores, function(i, id) {
            var data = products.selected_stores_data[id];
            jQuery('#available-store-' + id).addClass('selected');
        });
        jQuery('#product-stores').closest('.panel').addClass('active');
    }

    // Select sort
    if(products.selected_sort) {
        $('#product-sort li a').each(function(i, e) {
            var elem = $(e);
            if(elem.data('sort') == products.selected_sort) {
                elem.addClass('selected');
            } else {
                elem.removeClass('selected');
            }
        });
    } else {
        $('#product-sort a.selected').removeClass('selected');
        $('#product-sort li:first a').addClass('selected');
    }

    // Select view
    if(products.selected_view) {
        $('.shop-view li a').each(function(i, e) {
            var elem = $(e);
            if(elem.data('view') == products.selected_view) {
                elem.addClass('selected');
            } else {
                elem.removeClass('selected');
            }
        });
    } else {
        $('.shop-view a.selected').removeClass('selected');
        $('.shop-view li:first a').addClass('selected');
    }
}

function updateEmbeddedProducts($list) {
    if(typeof embed_shop_user_id !== 'undefined') {
        // TODO: remove product-container later?
        $list.find('.product-medium').each(function(i, element) {
            var buy_url = $(element).find('.btn-product-buy').attr('href');
            buy_url = buy_url.replace('Shop/0/', 'Ext-Shop/' + embed_shop_user_id + '/');
            $('.product-image-container > a, .caption > h4 > a', element).attr('href', buy_url);
            $('.product-image-container > a, .caption a', element).attr('target', '_blank');
            var looks_elem = $('.caption a.looks', element);
            var looks_href = looks_elem.attr('href');
            looks_elem.attr('href', looks_href + '?aid=' + embed_shop_user_id + '&alink=Ext-Shop');
            $('.hover', element).remove();
        });
    } else if(typeof profile_shop_user_id !== 'undefined') {
        // TODO: remove product-container later?
        $list.find('.product-medium').each(function(i, element) {
            var buy_url = $(element).find('.btn-product-buy').attr('href');
            if(typeof buy_url != 'undefined') {
                buy_url = buy_url.replace('Shop/0/', 'Profile/' + profile_shop_user_id + '/');
                $('.hover .btn-product-buy', element).attr('href', buy_url);
            }
        });
    }
}

function renderProducts(products) {
    $('#product-list > .product-list').empty();
    $('#product-list > h3').text(products.browse_text);

    renderPage(products);

    var product_list = $('#product-list');
    product_list.children().show();
    product_list.find('#product-infotext').remove();
    if(products.extra_html) {
        product_list.children().hide();
        product_list.prepend(products.extra_html);
    }

    filterCriteria(products);

    resetInfiniteScroll();
}
