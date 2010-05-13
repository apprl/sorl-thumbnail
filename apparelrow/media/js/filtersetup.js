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
    var rangefield = jQuery("input[name=1:vp.price:range]");
    //rangefield.hide();
    jQuery("#price-slider").slider({
        range: true,
        min: pricerange.min,
        max: pricerange.max,
        step: 10,
        values: rangefield.val().split(","),
        animate: 'fast',
        slide: function(event, ui) {
                rangefield.val(jQuery(this).slider('values', 0) + "," + jQuery(this).slider('values', 1));
        },
        change: function(event, ui) {
            jQuery(this).addClass('selected');
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
    // Initially hide all subcategories
    jQuery('#product-category li > ul').hide();
    jQuery('#product-category li > a').click(function() {
        var $this = jQuery(this);
            $this.toggleClass('selected');
        
        var subCategories = $this.next();
        
        if(subCategories.length > 0) {
            if($this.hasClass('selected')) {
                subCategories.find('a').addClass('selected');
            } else {
                subCategories.find('a').removeClass('selected');
            }
            
            subCategories.slideToggle();
            return false;
        }
        return true;
    });
});
