jQuery(document).ready(function() {
    // Make option panels popups
    jQuery('.options').addClass('popup');
    jQuery('.options button').click(function() {
        jQuery(this).parents('.popup').hide();
        jQuery(this).parents('li.active').removeClass('active');
        
    });
    jQuery('.options form').submit(function() {
        if(jQuery(this).parents('.options').find('.selected').length > 0) {
            jQuery(this).parents('.options').siblings('a').addClass('selected');
        } else {
            jQuery(this).parents('.options').siblings('a').removeClass('selected');
        }
    });

    jQuery('#product-options > li > a').click(function() {
        
        if(!jQuery(this).parent().is(".active")) {
            jQuery('#product-options .options').hide();
            jQuery('#product-options li.active').removeClass('active');
        }
        
        jQuery(this).parent().toggleClass('active');
        jQuery(this).next('.options').slideToggle('fast');
        
        return false;
    });
    // Price slider
    
    var rangemin = jQuery("input[name=pricerange_min]");
    var rangemax = jQuery("input[name=pricerange_max]");
    
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
        step: 10,
        values: [rangemin.val(), rangemax.val()],
        animate: 'fast',
        slide: function(event, ui) {
            rangemin.val(jQuery(this).slider('values', 0));
            rangemax.val(jQuery(this).slider('values', 1));
        },
        change: function(event, ui) {
            jQuery(this).addClass('selected');
            rangemin.val(jQuery(this).slider('values', 0));
            rangemax.val(jQuery(this).slider('values', 1));
        }
     });
    // Brand search
    jQuery("input[name=brand]").keyup(function(e) {
        var s = jQuery(this).val();
        if(s == "") {
            jQuery('#product-manufacturers ul > li').show();
            return;
        }
        jQuery('#product-manufacturers ul > li').filter(function(index) {
            return jQuery(this).text().toLowerCase().indexOf(s.toLowerCase()) < 0;
        }).hide();
        jQuery('#product-manufacturers ul > li').filter(function(index) {
            return jQuery(this).text().toLowerCase().indexOf(s.toLowerCase()) >= 0;
        }).show();
    });
    // Toggle selected on categories with selected subcategories
    jQuery('> a', '#product-category li:has(li > a.selected)').addClass('selected');
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
                
        var subCategories = $this.next();
        
        if(subCategories.length > 0) {
            if($this.hasClass('selected')) {
                if(subCategories.is(':visible')) {
                    subCategories.find('a').removeClass('selected');
                    $this.removeClass('selected');
                }
            } else {
                subCategories.find('a').addClass('selected');
                if(subCategories.is(':hidden'))
                    $this.toggleClass('selected');
            }
            
            subCategories.slideToggle();
            return false;
        } else {
            $this.toggleClass('selected');
        }
        return true;
    });
});
