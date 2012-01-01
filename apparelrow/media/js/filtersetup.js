jQuery(document).ready(function() {
    // Price slider
    var rangemin = jQuery("input[name=pricerange_min]");
    var rangemax = jQuery("input[name=pricerange_max]");

    var display_min = jQuery('#price-min span');
    var display_max = jQuery('#price-max span');

    jQuery('#price-slider').siblings('input[type=text]').blur(function(e) {
        var slider = jQuery('#price-slider').data('slider');
        var values = [
            parseInt(jQuery(this).siblings('input[type=text]').val()),
            (isNaN(this.value)) ? false : parseInt(this.value)
        ];
        
        // values = [min, max]
        if(this.name == 'pricerange_min') {
            values.reverse();
            var min = parseInt(slider.option('min'));
            if(!values[0] || values[0] < min) {
                values[0] = min;
            } else if(values[0] >= values[1]) {
                values[0] = values[1] - 1;
            }
        } else {
            var max = parseInt(slider.option('max'));
            if(!values[1] || values[1] > max) {
                values[1] = max;
            } else if(values[1] <= values[0]) {
                values[1] = values[0] + 1;
            }
        }
        
        slider.option('values', values);
        return true;
    });

    jQuery("#price-slider").slider({
        range: true,
        min: pricerange.min,
        max: pricerange.max,
        step: 1,
        values: [rangemin.val(), rangemax.val()],
        animate: 'fast',
        slide: function(event, ui) {
            rangemin.val(jQuery(this).slider('values', 0));
            rangemax.val(jQuery(this).slider('values', 1));
            display_min.text(jQuery(this).slider('values', 0));
            if(max_value >= 10000) {
                display_max.text('10000+');
            } else {
                display_max.text(jQuery(this).slider('values', 1));
            }
        },
        change: function(event, ui) {
            rangemin.val(jQuery(this).slider('values', 0));
            rangemax.val(jQuery(this).slider('values', 1));
            display_min.text(jQuery(this).slider('values', 0));
            max_value = jQuery(this).slider('values', 1);
            if(max_value >= 10000) {
                display_max.text('10000+');
            } else {
                display_max.text(jQuery(this).slider('values', 1));
            }
            if(event.originalEvent) {
                jQuery(this).addClass('selected');
                jQuery(this).parents('form').submit();
            }
        }
    });

    // Brand search
    ManufacturerBrowser.init();
    var _manufacturerSearchTimeout;
    jQuery("input[name=brand]")
        .keyup(function(e) {
            var name = this.value; 
            if(_manufacturerSearchTimeout)
                clearTimeout(_manufacturerSearchTimeout);
            _manufacturerSearchTimeout = setTimeout(function() { ManufacturerBrowser.filterByName(name) }, 500);
        })
        .focus(function(e) { 
            if(this.value == this.defaultValue) {
                this.value = '';
                jQuery(this).removeClass('default');
            }
        })
        .blur(function(e) { 
            if(this.value == '') {
                this.value = this.defaultValue; 
                jQuery(this).addClass('default');
            }
        });
    ;
    
    // Initially hide all subcategories
    jQuery('#product-category li > ul').hide();
    // Except those with selected categories inside
    jQuery('> ul', '#product-category li:has(a.selected)').show();
    // Also show those which should not be filtered
    jQuery('#product-category li:not(.to_filter)').parents('.to_filter').removeClass('to_filter').find('ul').show();
    // And filter all others
    jQuery('#product-category li.to_filter').removeClass('to_filter').addClass('filtered');

    jQuery('#product-category li > a').click(function() {
        var $this = jQuery(this);
        if($this.hasClass('selected')) {
            $this.removeClass('selected').parent().find('a').removeClass('selected');

            var subCategories = $this.next();
            if(subCategories.length > 0) {
                subCategories.slideUp('slow', function() {
                    jQuery(this).find('ul').hide()
                });
                return false;
            }
        } else {
            // Deselect parent category
            $this.parent().parent().prev().removeClass('selected');
            // Hide too deep categories
            $this.parent().find('ul ul').slideUp();
            // Deselect all children
            $this.parent().find('a').removeClass('selected');
            // Select this
            $this.addClass('selected');
            // Show subcategories
            var subCategories = $this.next();
            if(subCategories.length > 0) {
                subCategories.slideDown();
                return false;
            }
        }
        return true;
    });
});

var ManufacturerBrowser = {
    canFetch: true,
    brandPage: 1,
    brandName: '',
    $availableList: null,
    
    init: function() {
        var self = ManufacturerBrowser;
        this.$availableList = jQuery('#available-manufacturers');
    },
    
    reset: function() {
        this.$availableList.html('');
        this.canFetch = true;
        this.brandPage = 1;
    },
    
    renderItem: function(item, $list) {
        // FIXME: When we render template on server, drop this method all together
        var $a = jQuery('<a>')
            .attr('href', browse_url + '?manufacturer=' + item[0])
            .attr('id', 'available-manufacturer-' + item[0])
            .text(item[1]);
        
        if(jQuery('#manufacturer-' + item[0]).length > 0)
            $a.addClass('selected');
        
        jQuery('<li>')
            .append($a)
            .appendTo(this.$availableList);
    },
    
    fetchNextPage: function() {
        this.brandPage++;
        this.fetchManufacturers();
    },
    
    filterByName: function(name) {
        this.reset();
        this.brandName = name;
        this.fetchManufacturers();
    },
    
    fetchManufacturers: function() {
        var self  = this;
        var query = 'mpage=' + this.brandPage;
        
        if(this.brandName && this.brandName.length > 0)
            query += '&mname=' + this.brandName;
        
        if(typeof getQuery == 'function')
            query += '&' + jQuery.param(getQuery());
        
        self.canFetch = false;
        
        jQuery.getJSON(browse_manufacturers_url + '?' + query,
            function(response) {
                if(jQuery.isArray(response) && response.length > 0) {
                    jQuery.each(response, function(i, manufacturer) {
                        self.renderItem(manufacturer);
                    });
                    self.canFetch = true;
                }
            }
        );
    }
};



