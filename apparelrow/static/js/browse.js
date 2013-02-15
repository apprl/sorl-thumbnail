jQuery(document).ready(function() {
    // Initialize jquery history plugin with our filter
    var firstLoad = true;
    jQuery.history.init(function(hash) {
        // This is slightly contrived. On first load, only filter if we have something in the hash.
        // If so, hide the content to avoid flashing the products in the page, then show content again
        // and render products.
        // If it's not the first load, just filter products.
        if(firstLoad) {
            firstLoad = false;
            if(hash != "") {
                jQuery('#content').hide();
                doFilter(hash, function(response) {
                    jQuery('#content').show();
                    renderProducts(response);
                    updateSelected(response);
                    calculateProductLayout();
                });
            } else {
                // No hash, but we must selected all genders if no gender is selected
                // TODO: Move this to a function if more functionality is needed.
                // FIXME: Is this necessary?
                if(!jQuery('#product-gender li > a').hasClass('selected')) {
                    jQuery('#product-gender li:first > a').addClass('selected');
                }
                calculateProductLayout();
            }
        } else {
            doFilter(hash, this.filterCallback);
            this.filterCallback = null;
        }
    });

    // Currency conversion
    currencyConversion(jQuery('#product-list').find('.price, .discount-price'));

    // Initially hide level 1 and 2 categories
    jQuery('#product-category .level-1, #product-category .level-2').hide();

    // Full reset button
    jQuery('#reset').click(function() {
        // Every selected element is deselected
        jQuery('#inner-container .selected').removeClass('selected');

        // Every active element is deactivated
        jQuery('#inner-container .active').removeClass('active');

        // Hide level 1 and 2 categories
        jQuery('#product-category .level-1, #product-category .level-2').hide();

        // Initiate individual reset for brands filter
        jQuery('#product-manufacturers').prev().find('.reset').click();

        // Initiate individual reset for stores filter
        jQuery('#product-stores').prev().find('.reset').click();

        // Select both genders
        jQuery('#product-gender li:first > a').addClass('selected');

        // Sort by
        jQuery('.browse-sort li:first a').addClass('selected');

        // Call getQuery with empty query and force reset
        filter(getQuery({}, true));

        // Reset autoscrolling
        jQuery(window)
            .data('first-scroll', true)
            .data('dont-scroll', false);

        return false;
    });

    // Individual reset button
    jQuery('#product-options .header .reset').click(function(e) {
        var link = jQuery(this);
        link.closest('li').next().find('.selected').removeClass('selected');
        link.parents('li.active').removeClass('active');

        switch(link.closest('li').next().attr('id')) {
            case 'product-price':
                // Move slider to min and max
                var slider = jQuery('#price-slider').data('slider');
                    slider.values([slider.option('min'), slider.option('max')]);
                break;

            case 'product-color':
                break;

            case 'product-manufacturers':
                jQuery('input[name=brand]').val('').blur();
                jQuery('#selected-manufacturers > li').remove();
                break;

            case 'product-stores':
                jQuery('#selected-stores > li').remove();
                break;

            default:
                return false;
        }

        filter(getQuery());
        return false;
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

    // Click handler for manufacturer option-popup
    jQuery('#available-manufacturers a').live('click', function(e) {
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
        var element = $(this);
        var selected_stores = $('#selected-stores');
        var id = 'store-' + getElementId(element);

        if(element.hasClass('selected')) {
            $('#' + id, selected_stores).click(); // selected class is removed in this click handler
        } else {
            element.addClass('selected');
            element.clone().attr('id', id).appendTo(
                $('<li>').prependTo(selected_stores)
            );
            filter(getQuery());
        }

        return false;
    });

    // Click handler for manufacturer search results element
    jQuery('#search-result-manufacturers a').live('click', function(e) {
        // Cancel search and reset browse filters
        ApparelSearch.cancel();
        jQuery('#reset').click();

        // Get current element and id
        var element = jQuery(this);
        var id = 'manufacturer-' + getElementId(element);

        // If not previously marked as selected, select it, add it to the
        // selected list and make sure the manufacturer filter is activated
        var element_available = jQuery('#available-manufacturer-' + id);
        if(!element_available.hasClass('selected')) {
            element_available.addClass('selected');
            element.clone().attr('id', id).appendTo(jQuery('<li>').prependTo(jQuery('#selected-manufacturers')));
            filter(getQuery());
        }
    });

    // Click handler for list of selected manufacturers
    jQuery('#selected-manufacturers a').live('click', function(e) {
        jQuery('#available-manufacturer-' + getElementId(this)).removeClass('selected');
        jQuery(this).closest('li').remove();
        filter(getQuery());

        return false;
    });

    // Click handler for list of selected stores
    $(document).on('click', '#selected-stores a', function(e) {
        $('#available-store-' + getElementId(this)).removeClass('selected');
        $(this).closest('li').remove();
        filter(getQuery());

        return false;
    });

    // Sort by
    jQuery(document).on('click', '.browse-sort li a', function(e) {
        jQuery('.browse-sort li a').removeClass('selected');
        jQuery(this).addClass('selected');
        filter(getQuery());
        return false;
    });

    // Set selected and clear selected from related element and then call filter
    function resetGender(element) {
        if(!element.hasClass('.selected')) {
            // XXX: might want to create a reset function
            jQuery('#reset').click();
            // Reset call above will select all genders, deselect all genders
            // and only select men or women.
            jQuery('#product-gender li:first > a').removeClass('selected');
            element.addClass('selected');
            filter(getQuery());
        }
    }

    // Product gender filter
    jQuery('#product-gender li > a').click(function() {
        var element = jQuery(this);
        if(!element.hasClass('.selected')) {
            element.addClass('selected');
            element.parent().siblings().find('a').removeClass('selected');
            filter(getQuery());
        }
        return false;
    });

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

    function fetchPage(page, callback) {
        filter(getQuery({page: page}), function() {
            renderPage.apply(null, arguments);
            callback && callback();
        });
    }

    function parsePage(link) {
        var attr_href = link.attr('href');
        if (typeof attr_href !== 'undefined' && attr_href !== false) {
            return parseInt(link.attr('href').split('=')[1], 10);
        }
        return false;
    }

    infiniteScroll(function(callback) {
        var page = parsePage(jQuery('.pagination .next'));
        if (page) {
            fetchPage(page, callback);
        }
    });

    jQuery('.pagination a').live('click', function(e) {
        var $this = jQuery(this);
        $this.addClass('btn-disabled hover').find('span').text($this.data('loading-text'));
        var page = parsePage($this);
        if (page) {
            fetchPage(page);
        }

        // Set up auto-scrolling
        jQuery(window).data('dont-scroll', false);

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
 * GET QUERY
 *
 * Create a query object and populate it with selected filters. Also make sure
 * that if there are selected filters, mark that filter category as active.
 */
window.getQuery = function(query, reset) {
    query = query || {}
    reset = typeof(reset) != 'undefined' ? reset : false;

    sort_by = jQuery('.browse-sort li a.selected').attr('data-sort');
    if(sort_by != 'pop') {
        query['sort'] = sort_by;
    }

    category_list = getElementIds(jQuery('#product-category li > a.selected'));
    if(category_list.length > 0) {
        query['category'] = category_list.join(',');
    }

    manufacturer_list = getElementIds(jQuery('#selected-manufacturers li > a'));
    if(manufacturer_list.length > 0) {
        query['manufacturer'] = manufacturer_list.join(',');
        jQuery('#product-manufacturers').addClass('active').prev().addClass('active');
    } else {
        jQuery('#product-manufacturers').removeClass('active').prev().removeClass('active');
    }

    store_list = getElementIds(jQuery('#selected-stores li > a'));
    if(store_list.length > 0) {
        query['store'] = store_list.join(',');
        jQuery('#product-stores').addClass('active').prev().addClass('active');
    } else {
        jQuery('#product-stores').removeClass('active').prev().removeClass('active');
    }

    gender_list = getElementIds(jQuery('#product-gender li > a.selected'));
    if(gender_list.length > 0 && gender_list[0]) {
        query['gender'] = gender_list[0];
    }

    color_list = getElementIds(jQuery('#product-color a.color.selected'));
    if(color_list.length > 0) {
        query['color'] = color_list.join(',');
        // Mark color filter as active
        jQuery('#product-color').prev().addClass('active');
    }

    pattern_list = getElementIds(jQuery('#product-color a.pattern.selected'));
    if(pattern_list.length > 0) {
        query['pattern'] = pattern_list.join(',');
        // Mark color filter as active
        jQuery('#product-color').prev().addClass('active');
    }

    if(color_list.length == 0 && pattern_list.length == 0) {
        jQuery('#product-color').prev().removeClass('active');
    }

    if(jQuery('#price-slider').is('.selected')) {
        query['price'] =
              jQuery("input[name=pricerange_min]").val()
            + ','
            + jQuery("input[name=pricerange_max]").val();
        jQuery('#product-price').prev().addClass('active');
    }

    if(jQuery('#discount-price').is('.selected')) {
        query['discount'] = 1;
        jQuery('#product-price').prev().addClass('active');
    }

    if(!reset && window.location.hash.length > 0) {
        var pairs = window.location.hash.substr(1).split('&');
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

function filter(query, callback) {
    // FIXME: History hack. It is not possible to set window.location.hash and then call
    // doFilter(...) as that will invoke the call twice with a different callback
    // The current workaround is this:
    // 1) Only let the jQuery.history callback invoke doFilter()
    // 2) If a callback other than renderProducts is required, set the filterCallback property
    //    It will be cleaned up after first use
    // Anyone with a better, cleaner idea how to solve this, just go ahead and implement it. This doesn't feel so nice
    jQuery.history.filterCallback = callback;
    window.location.hash = decodeURIComponent(jQuery.param(query, true)) || '!';
}
function doFilter(query, callback) {
    if(!query.hasOwnProperty('page')) {
        jQuery('#product-list').css('opacity', 0.3);
    }
    jQuery.getJSON(browse_url, query, callback || renderProducts);
}
function renderPage(products) {
    var $html = $(products.html);
    var $list = $html.filter('ul.list');
    var $pagination = $html.filter('.pagination');

    currencyConversion($list.find('.price, .discount-price'));

    jQuery('#product-list > ul.list').append($list.html());
    jQuery('.pagination').html($pagination.html());

    jQuery('#product-list').trigger('post_browse_render');

    query = getQuery();
    if('f' in query) {
        jQuery('#product-count a').hide();
        //jQuery('#product-gender').show();
    } else {
        jQuery('#product-count a').show();
        // Special case, only hide gender if we are not on the wardrobe page
        // TODO / FIXME: better solution?
        if(window.location.pathname.indexOf('likes') == -1) {
            jQuery('#product-gender').hide();
        }
    }

    if(window.location.hash && window.location.hash != '#!') {
        jQuery('#reset').show()
    } else {
        jQuery('#reset').hide()
    }

    jQuery('#product-list').css('opacity', 1);
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

    if('stores' in criteria_filter && !$('#product-stores').prev().hasClass('active')) {
        $('#available-stores').html('');
        $.each(criteria_filter['stores'], function(i, store) {
            var $a = $('<a>')
                .attr('href', browse_url + '?store=' + store[0])
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
                this_element.find('.category-count').text('(' + criteria_filter['categories'][this_element_id] + ')');
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
    if(products.selected_categories && products.selected_categories.length > 0) {
        // If we have a select category
        jQuery.each(products.selected_categories, function(i, id) {
            var category = jQuery('#category-' + id).addClass('selected');
            category.siblings('ul').show();
            category.parents('ul').show();
        });
    }

    // Select gender
    if(products.selected_gender && products.selected_gender.length > 0) {
        jQuery.each(products.selected_gender, function(i, id) {
            jQuery('#option-' + id).addClass('selected');
        });
    } else {
        jQuery('#product-gender li:first > a').addClass('selected');
    }

    // Select price
    if(products.selected_price) {
        jQuery('#price-slider').data('slider').values(products.selected_price);
        jQuery('#product-price').prev().addClass('active');
    }

    // Select discount
    if(products.selected_discount) {
        jQuery('#discount-price').addClass('selected');
    }

    // Select colors
    if(products.selected_colors && products.selected_colors.length > 0) {
        jQuery.each(products.selected_colors, function(i, id) {
            jQuery('#option-' + id).addClass('selected');
        });
        jQuery('#product-color').prev().addClass('active');
    }

    // Select patterns
    if(products.selected_patterns && products.selected_patterns.length > 0) {
        jQuery.each(products.selected_patterns, function(i, id) {
            jQuery('#option-' + id).addClass('selected');
        });
        jQuery('#product-color').prev().addClass('active');
    }

    // Select brands
    if(products.selected_brands && products.selected_brands.length > 0) {
        jQuery.each(products.selected_brands, function(i, id) {
            var data = products.selected_brands_data[id];
            jQuery('#available-manufacturer-' + id).addClass('selected');
            jQuery('<li>').append(
                jQuery('<a>').attr({id: 'manufacturer-' + id, href: data['href']}).text(data['name'])
            ).prependTo('#selected-manufacturers');
        });
        jQuery('#product-manufacturers').addClass('active').prev().addClass('active');
    }

    // Select store
    if(products.selected_stores && products.selected_stores.length > 0) {
        jQuery.each(products.selected_stores, function(i, id) {
            var data = products.selected_stores_data[id];
            jQuery('#available-store-' + id).addClass('selected');
            jQuery('<li>').append(
                jQuery('<a>').attr({id: 'store-' + id, href: data['href']}).text(data['name'])
            ).prependTo('#selected-stores');
        });
        jQuery('#product-stores').addClass('active').prev().addClass('active');
    }

    // Select sort
    if(products.selected_sort) {
        jQuery('.browse-sort li a').each(function(i, e) {
            var elem = jQuery(e);
            if(elem.attr('data-sort') == products.selected_sort) {
                elem.addClass('selected');
            } else {
                elem.removeClass('selected');
            }
        });
    }
}

// Run every time new products are loaded
function calculateProductLayout() {
    jQuery('.sold-out').text(gettext('SOLD OUT'));
}

function renderProducts(products) {
    $('#product-list > ul.list').empty();
    if('selected_discount' in products && products['selected_discount']) {
        product_count_text = $('#product-count span').text(
            interpolate(ngettext(
                '%s product on sale',
                '%s products on sale',
                products.paginator.count
            ), [products.paginator.count])
        );
    } else {
        product_count_text = $('#product-count span').text(
            interpolate(ngettext(
                '%s product',
                '%s products',
                products.paginator.count
            ), [products.paginator.count])
        );
    }
    if('help_text' in products) {
        product_count_text.prepend(products.help_text + ', ');
    }
    renderPage(products);

    var product_list = jQuery('#product-list');
    product_list.find('#product-infotext').remove();
    if(products.follow_html) {
        product_list.prepend(products.follow_html);
    }

    filterCriteria(products);
    calculateProductLayout();
}
