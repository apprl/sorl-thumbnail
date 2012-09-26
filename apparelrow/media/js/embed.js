jQuery(document).ready(function() {
    jQuery('.product').enableApprlTooltip();

    // Hide hotspots and only show them on mouseenter
    jQuery('.hotspot').hide();
    jQuery('.look-photo').live('mouseenter', function() {
        jQuery('.hotspot', this).stop(true, true).fadeIn(300);
    }).live('mouseleave', function() {
        jQuery('.hotspot', this).stop(true, true).fadeOut(300);
    });
});
