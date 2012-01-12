var pagination = {
    recalculate: function(page) {
        var on_ends      = 2;   // FIXME: These constants should come from the server
        var on_each_side = 3;
        var num_pages = this.data.paginator.num_pages;
        
        this.data.pagination.right = null;
        this.data.pagination.left  = null;
        this.data.pagination.mid   = [];
        
        if(num_pages <= (on_ends * 2) + (on_each_side * 2)) {
            for(var i = 1; i <= num_pages; i++) {
                this.data.pagination.mid.push(i);
            }
        } else {
            if(page <= on_ends + on_each_side + 1) {
                for(var i = 1; i <= page; i++) {
                    this.data.pagination.mid.push(i);
                }
            } else {
                this.data.pagination.left = [];
                for(var i = 1; i <= on_ends; i++) {
                    this.data.pagination.left.push(i);
                }
                for(var i = page - on_each_side; i <= page; i++) {
                    this.data.pagination.mid.push(i);
                }
            }
            
            if(page >= num_pages - (on_ends + on_each_side + 1)) {
                for(var i = page + 1; i <= num_pages; i++) {
                    this.data.pagination.mid.push(i);
                }
            } else {
                this.data.pagination.right = [];
                for(var i = page + 1; i <= on_each_side + page; i++) {
                    this.data.pagination.mid.push(i);
                }
                for(var i = num_pages - on_ends + 1; i <= num_pages; i++) {
                    this.data.pagination.right.push(i);
                }                        
            }
        }
                        
        this.data.next_page_number     = (page < num_pages) ? page + 1 : null;
        this.data.previous_page_number = (page > 1)         ? page - 1 : null;
        this.data.number = page;
    },
    data: pagination_data,
    render: function() {
        try {
            $('.pagination').html($('#pagination_template').render({products: this.data}));
        } catch(e) {
            console.log(e)
        }
    }
};

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
                    adjustProductListHeight();
                });
            } else {
                // No hash, but we must selected all genders if no gender is selected
                // TODO: Move this to a function if more functionality is needed.
                // FIXME: Is this necessary?
                if(!jQuery('#product-gender li > a').hasClass('selected')) {
                    jQuery('#product-gender li:first > a').addClass('selected');
                }
                adjustProductListHeight();
            }
        } else {
            doFilter(hash, this.filterCallback);
            this.filterCallback = null;
        }
    });

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

        // Select both genders
        jQuery('#product-gender li:first > a').addClass('selected');

        // Call getQuery with empty query and force reset
        filter(getQuery({}, true));

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

    function scrollTo(page) {
        if((jQuery(window).height() - jQuery('body').scrollTop()) < 300)
            jQuery('body').scrollTop(0);

        if(page == 0 || page > pagination.data.paginator.num_pages)
            return false;
        
        if(jQuery('#page-' + page).length == 0) {
            filter(getQuery({page: page}), function(response) {
                renderPage(response);
                jQuery('#product-list').data('scrollable').seekTo(jQuery('#page-' + page).index(), 400);
            });
        } else {
            jQuery('#product-list').data('scrollable').seekTo(jQuery('#page-' + page).index(), 400);
        }
    }

    jQuery(document).keydown(function(e) {
        if(e.keyCode == 37 || e.keyCode == 39) {
            var index = jQuery('#product-list').data('scrollable').getIndex(),
                currentPageId = getNumericElementId(jQuery('#product-list > ul.list > li:eq(' + index + ')'), true),
                page = e.keyCode == 37 ? currentPageId - 1 : currentPageId + 1;

            scrollTo(page);
        }
    });

    jQuery('.pagination a').live('click', function(e) {
        // FIXME: Move out logic to section that handles page-swapping
        
        var link = jQuery(this);
        var page = parseInt(link.attr('href').split('=')[1], 10);
        
        scrollTo(page);
        return false;
    });
    jQuery('#product-list').scrollable({
        items: 'ul.list',
        keyboard: false,
        onBeforeSeek: function(event, index) {
            var target = jQuery('#product-list > ul.list > li:eq(' + index + ')');
            var pageNum = parseInt(target.attr('id').split('-')[1], 10);
            if(target.is(':empty')) {
                filter(getQuery({page: pageNum}), function(response) {
                    renderPage(response);
                    pagination.recalculate(pageNum);
                    pagination.render();
                });
            } else {
                pagination.recalculate(pageNum);
                pagination.render();
            }
        },
        onSeek: adjustProductListHeight
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
function getQuery(query, reset) {
    query = query || {}
    reset = typeof(reset) != 'undefined' ? reset : false;

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

function getElementId(element, numeric) {
    return jQuery(element).attr('id').split('-').pop()
}

function getNumericElementId(element) {
    return parseInt(jQuery(element).attr('id').split('-').pop(), 10);
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
    jQuery.getJSON(browse_url, query, callback || renderProducts);
}
function renderPage(products) {
    // Find the pages in the response
    var pages = jQuery('ul.list > li', products.html)
        // Append each page to appropriate place
        .each(function(i, page) {
            var existing = jQuery('#' + this.id);
            if(existing.length == 0) {
                var existingPages = jQuery('#product-list > ul.list > li');
                var nextPage = existingPages.filter(function(i) { return getNumericElementId(this) > getNumericElementId(page) }).first();
                // There are pages that should be after this one in the list
                if(nextPage.length == 1) {
                    nextPage.before(page);
                // This should be the last page in the list
                } else if(existingPages.length > 0) {
                    existingPages.last().after(page);
                // There are no other pages
                } else {
                    jQuery('#product-list > ul.list').append(page);
                }
            } else {
                existing.replaceWith(page);
            }
        });

    jQuery('#product-list').trigger('post_browse_render');

    query = getQuery();
    if('f' in query) {
        jQuery('#product-count a').hide();
        jQuery('#product-gender').show();
    } else {
        jQuery('#product-count a').show();
        // Special case, only hide gender if we are not on the wardrobe page
        // TODO / FIXME: better solution?
        if(window.location.pathname.indexOf('wardrobe') == -1) {
            jQuery('#product-gender').hide();
        }
    }

    if(window.location.hash && window.location.hash != '#!') {
        jQuery('#reset').show()
    } else {
        jQuery('#reset').hide()
    }
}

/**
 * Apply filter on available browse options.
 */
function filterCriteria(criteria_filter) {
    if('manufacturers' in criteria_filter && !jQuery('#product-manufacturers').prev().hasClass('active')) {
        ManufacturerBrowser.reset(true);

        jQuery.each(criteria_filter['manufacturers'], function(i, manufacturer) {
            ManufacturerBrowser.renderItem(manufacturer);
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
        jQuery('#product-category > li[class!=filtered]:first').addClass('first');
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

        jQuery('#price-ruler .min').text(min);
        jQuery('#price-ruler .mid').text(mid);
        if(max >= 10000) {
            jQuery('#price-ruler .max').text('10000+');
        } else {
            jQuery('#price-ruler .max').text(max);
        }

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
}

function adjustProductListHeight() {
    // Calculate height of product-list
    var height = 0;
    jQuery('#product-list').children().each(function () {
        height += $(this).height();
    });

    jQuery('#product-list').height(height);
}

function renderProducts(products) {
    $('#product-list > ul.list').empty();
    product_count_text = $('#product-count span').text(
        interpolate(ngettext(
            '%s product', 
            '%s products', 
            products.paginator.count
        ), [products.paginator.count])
    );
    if('help_text' in products) {
        product_count_text.prepend(products.help_text + ', ');
    }
    renderPage(products);
    pagination.data = products;
    pagination.recalculate(0);
    pagination.render();

    var product_list = jQuery('#product-list');
    product_list.data('scrollable').begin();
    product_list.find('#product-infotext').remove();
    if(products.follow_html) {
        product_list.prepend(products.follow_html);
    }

    filterCriteria(products);
    
    adjustProductListHeight();
}
