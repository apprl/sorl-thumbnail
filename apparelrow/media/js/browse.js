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
            $('#pagination').html($('#pagination_template').render({products: this.data}));
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
                });
            } else {
                // No hash, but we must selected all genders if no gender is selected
                // TODO: Move this to a function if more functionality is needed.
                // FIXME: Is this necessary?
                if(!jQuery('#product-gender li > a').hasClass('selected')) {
                    jQuery('#product-gender li:first > a').addClass('selected');
                }
            }
        } else {
            doFilter(hash, this.filterCallback);
            this.filterCallback = null;
        }
    });
    // Tooltips FIXME: Fix this, so it works with ajax fetched stuff and looks nice
    // jQuery('#product-list > ul > li').tooltip({ effect: 'slide', position: 'bottom center', offset: [170, 0], relative: true });
    // Fixed scrolling
    //jQuery('#content').fixedscroll();

    jQuery('#product-category .level-1, #product-category .level-2').hide();

    // Reset button
    jQuery('#reset').click(function() {
        jQuery('.selected').removeClass('selected');
        jQuery('#product-category .level-1, #product-category .level-2').hide();
        jQuery('#product-manufacturers .reset').click();
        jQuery('#product-gender li:first > a').addClass('selected'); // Select all genders
        // Call getQuery with empty query and reset true
        filter(getQuery({}, true));
        return false;
    });
    jQuery('.options .reset').click(function(e) {
        var link = jQuery(this);
        
        link
            .parents('.options').hide()
            .parents('li.active').removeClass('active')
            .find('a.selected').removeClass('selected');

        switch(link.closest('li').attr('id')) {
            case 'product-price':
                // Move slider to min and max
                var slider = jQuery('#price-slider').data('slider');
                    slider.values([slider.option('min'), slider.option('max')]);
                break;
            case 'product-color':
                // Uncheck all colours
                jQuery('ul > li', link.closest('.popup'))
                    .find('.selected')
                    .removeClass('selected');
                    
                break;
            case 'product-manufacturers':
                jQuery("input[name=brand]")
                    .val('')
                    .keyup()
                    .blur()
                ;
                
                jQuery('#available-manufacturers > li > a.selected')
                    .removeClass('selected');
                
                jQuery('#selected-manufacturers > li')
                    .remove();
                
                break;
            default:
                return false;
        }
        
        filter(getQuery());
        return false;
    });

    jQuery('#product-price form').submit(function() {
        filter(getQuery());
        return false;
    });
    jQuery('#product-color form').submit(function() {
        filter(getQuery());
        return false;
    });

    jQuery('#product-manufacturers form').submit(function() {
        return false;
    });
    jQuery('#available-manufacturers a').live('click', function(e) {
        var $this = jQuery(this);
        var $ul   = jQuery('#selected-manufacturers');
        var id    = 'manufacturer-' + this.id.split('-').pop();
        
        if($this.is('.selected')) {
            jQuery('#' + id, $ul).click();
        } else {
            $this
                .clone()
                .attr('id', id)
                .appendTo(
                    $('<li>')
                        .prependTo($ul)
                );
            
            delayedFilter(getQuery());
            jQuery('#product-manufacturers>a').addClass('selected');
        }
        
        $this.toggleClass('selected');
        return false;
    });
    jQuery('#selected-manufacturers a').live('click', function(e) {
        var $li = jQuery(this).closest('li');

        var id = parseInt(jQuery(this).attr('id').split('-').pop(), 10);
        jQuery('#available-manufacturer-' + id).removeClass('selected');
        
        if($li.siblings().length == 0) 
            jQuery('#product-manufacturers>a').removeClass('selected');
        
        $li.remove();
        delayedFilter(getQuery());
        
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

    // Handles click on women in main navigation on browse page
    jQuery('#nav-main .women, #footer .women').click(function() {
        resetGender(jQuery('#product-gender li.women > a'));
        return false;
    });

    // Handles click on men in main navigation on browse page
    jQuery('#nav-main .men, #footer .men').click(function() {
        resetGender(jQuery('#product-gender li.men > a'));
        return false;
    });

    jQuery('#product-gender li > a').click(function() {
        var element = jQuery(this);
        if(!element.hasClass('.selected')) {
            element.addClass('selected');
            element.parent().siblings().find('a').removeClass('selected');
            filter(getQuery());
        }
        return false;
    });
    jQuery('#product-color li > a').click(function() {
        if(!jQuery(this).hasClass('filtered')) {
            jQuery(this).toggleClass('selected');
        }
        return false;
    });
    jQuery('#product-category li > a').click(function() {
        filter(getQuery());
        return false;
    });

    function scrollTo(page) {
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
                currentPageId = parseInt(jQuery('#product-list > ul.list > li:eq(' + index + ')').attr('id').split('-').pop(), 10),
                page = e.keyCode == 37 ? currentPageId - 1 : currentPageId + 1;

            scrollTo(page);
        }
    });

    jQuery('#pagination a').live('click', function(e) {
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
        }
    });
    
    /**
     * BROWSE PAGE DEFAULTS
     * This allows manipulating the browse page interface on page load 
     * from the query string.
     * 
     * Syntax
     *  ?defaults=action|argument&...
     *  
     *  action      An named action see switch statement below
     *  argument    Optional argument passed with action
     * 
     * Any number of 'defaults' query parameters may be present
     * The actions will be performed in the same order as they appear in
     * the query string
     * 
     */
    jQuery.each(location.search.split('&'), function(i, e) {
        var pair = e.split('=');
        if(pair[0] != 'defaults') return;
        var value = unescape(pair[1]).split('|');
        
        switch(value[0]) {
            case 'manufacturer-dialog':
                // Show manufacturers filter dialog
                jQuery('#product-manufacturers > a').click();
                break;
                
            case 'manufacturer-dialog-filter':
                // Set and perform a filter om the manufacturer dialog
                jQuery('#product-manufacturers input[name=brand]')
                    .attr('value', value[1])
                    .keyup()
                    .focus();
                break;
                
            case 'price-dialog':
                // Show price dialog
                jQuery('#product-price > a').click();
                break;
                
            case 'color-dialog':
                // Show colour dialog
                jQuery('#product-color > a').click();
                break;
            
            default:
                console.error('Action ', value[0], ' not implemented');
        }
    });
});

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
    }

    gender_list = getElementIds(jQuery('#product-gender li > a.selected'));
    if(gender_list.length > 0 && gender_list[0]) {
        query['gender'] = gender_list[0];
    }

    color_list = getElementIds(jQuery('#product-color li > a.selected'));
    if(color_list.length > 0) {
        query['color'] = color_list.join(',');
    }

    if(jQuery('#product-price > a').is('.selected')) {
        query['price'] = 
              jQuery("input[name=pricerange_min]").val()
            + ',' 
            + jQuery("input[name=pricerange_max]").val();
    }

    if(!reset && location.hash.length > 0) {
        var pairs = location.hash.substr(1).split('&');
        for(var i = 0; i < pairs.length; i++) {
            keyval = pairs[i].split('=');
            if(keyval[0] == 'q') {
                query['q'] = keyval[1];
            }
        }
    }

    return query;
}
function getElementIds(elements) {
    return jQuery.map(elements, function(element) {
        return element.id.split('-').pop();
    });
}


var _delayedFilterTimerID;
function delayedFilter(query) {
    if(_delayedFilterTimerID)
        clearTimeout(_delayedFilterTimerID);
    
    _delayedFilterTimerID = setTimeout(function() { filter(query) }, 1000); 
}

function filter(query, callback) {
    // FIXME: History hack. It is not possible to set location.hash and then call
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

    function getId(el) {
        return parseInt(el.id.split('-').pop(), 10);
    }

    // Find the pages in the response
    var pages = jQuery('ul.list > li', products.html)
        // Append each page to appropriate place
        .each(function(i, page) {
            var existing = jQuery('#' + this.id);
            if(existing.length == 0) {
                var existingPages = jQuery('#product-list > ul.list > li');
                var nextPage = existingPages.filter(function(i) { return getId(this) > getId(page) }).first();
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

    if(location.hash && location.hash != '#!') {
        jQuery('#reset').show()
    } else {
        jQuery('#reset').hide()
    }
}

function filterCriteria(criteria_filter) {
    if('manufacturers' in criteria_filter && !jQuery('#product-manufacturers').hasClass('active')) {
        ManufacturerBrowser.reset();

        jQuery.each(criteria_filter['manufacturers'], function(i, manufacturer) {
            ManufacturerBrowser.renderItem(manufacturer);
        });
    }

    if('categories' in criteria_filter) {
        applyCriteriaFilter({
            'selector': '#product-category li > a',
            'criteria': criteria_filter['categories'],
            'add': function(o) { o.parent().addClass('filtered'); },
            'remove': function(o) {
                o.parents('.filtered').removeClass('filtered');
            },
        });
        jQuery('#product-category>li.first').removeClass('first');
        jQuery('#product-category>li[class!=filtered]:first').addClass('first');
    }

    if('colors' in criteria_filter) {
        applyCriteriaFilter({
            'selector': '#product-color .option-content li > a',
            'criteria': criteria_filter['colors'],
            'add': function(o) { o.addClass('filtered'); },
            'remove': function(o) { o.removeClass('filtered');  },
        });
    }

    if('pricerange' in criteria_filter) {
        var min = parseInt(criteria_filter.pricerange.min, 10),
            max = parseInt(criteria_filter.pricerange.max, 10),
            mid = parseInt(min + (max - min) / 2, 10);

        $('#price-ruler .min').text(min);
        $('#price-ruler .mid').text(mid);
        $('#price-ruler .max').text(max);

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

function applyCriteriaFilter(args) {
    //selector, criteria, cb_add, cb_remove
    jQuery(args.selector).each(function() {
        $this = jQuery(this);
        if (jQuery.inArray(parseInt(this.id.split('-')[1], 10), args.criteria) >= 0) {
            args.remove($this);
        } else {
            args.add($this);
        }
    });
}

function updateSelected(products) {
    function setSelected(selector) {
        jQuery(selector).addClass('selected');
    }

    function showCategories(list) {
        if(list && list.length > 0) {
            jQuery.each(list, function(i, id) {
                var category = jQuery('#category-' + id).addClass('selected');
                category.siblings('ul').show();
                category.parents('ul').show();
            });
        }
    }

    function selectList(list, selectorPrefix, parentSelector) {
        if(list && list.length > 0) {
            $.each(list, function(i, id) { setSelected(selectorPrefix + '-' + id) });
            if(parentSelector) {
                setSelected(parentSelector);
            }
        }
    }

    function selectGenderList(list, selectorPrefix) {
        if(list && list.length > 0) {
            jQuery.each(list, function(i, id) { setSelected(selectorPrefix + '-' + id) });
        } else {
            setSelected(jQuery('#product-gender li:first > a'));
        }
    }

    function selectBrandList(list, selectorPrefix, parentSelector) {
        if(list && list.length > 0) {
            jQuery.each(list, function(i, id) {
                var element = jQuery(selectorPrefix + '-' + id).addClass('selected');
                jQuery('<li>').append(
                    jQuery('<a>').attr({id: 'manufacturer-' + id, href: element.attr('href')}).text(element.text())
                ).prependTo('#selected-manufacturers');
            });
            if(parentSelector) {
                setSelected(parentSelector);
            }
        }
    }

    showCategories(products.selected_categories);
    selectBrandList(products.selected_brands, '#available-manufacturer', '#product-manufacturers > a');
    selectList(products.selected_colors, '#option', '#product-color > a');
    selectGenderList(products.selected_gender, '#option');

    if(products.selected_price) {
        setSelected('#product-price > a');
        var slider = jQuery('#price-slider').data('slider');
        slider.values(products.selected_price);
    }
}

function renderProducts(products) {
    $('#product-list > ul.list').empty();
    $('#product-count').text(
        interpolate(ngettext(
            '%s product', 
            '%s products', 
            products.paginator.count
        ), [products.paginator.count])
    );
    renderPage(products);
    pagination.data = products;
    pagination.recalculate(0);
    pagination.render();
    jQuery('#product-list').data('scrollable').begin();

    filterCriteria(products);
}
