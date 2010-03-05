jQuery(document).ready(function() {
    // Make option panels popups
    jQuery('.options').addClass('popup');
    jQuery('.options a.button').click(function() {
        $(this).parents('.popup').hide();
        $(this).parents('li.active').removeClass('active');
        return false;
    });
    jQuery('#product-options > li > a').click(function() {
        $(this).parent().toggleClass('active');
        $(this).next('.options').slideToggle('fast');
        return false;
    });
    // Brand search
    jQuery("input[name=brand]").keyup(function(e) {
        var s = jQuery(this).val();
        if(s == "") {
            $('#product-manufacturers > li').show();
            return;
        }
        $('#product-manufacturers > li').filter(function(index) {
            return jQuery(this).text().toLowerCase().indexOf(s.toLowerCase()) < 0;
        }).hide();
        $('#product-manufacturers > li').filter(function(index) {
            return jQuery(this).text().toLowerCase().indexOf(s.toLowerCase()) >= 0;
        }).show();
    });
    // Initially hide all subcategories
    jQuery('#product-category li > ul').hide();
    jQuery('#product-category li > a').click(function() {
        var $this = jQuery(this);
        $this.toggleClass('selected');
        var underCategories = $this.next();
        if(underCategories.length > 0) {
            var selected = underCategories.find('a.selected');
            if(selected.length <= 0) {
                underCategories.find('a').addClass('selected');
            }
            underCategories.slideToggle();
            return false;
        }
        return true;
    });
});
