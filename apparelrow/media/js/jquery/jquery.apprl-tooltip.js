// Apprl tooltips by Joel Bohman
(function($) {

    var closetimer = false;
    var tooltip = false;
    var tooltip_top = 0;
    var tooltip_left = 0;
    var last_id = false;

    function open(event) {
        var component = jQuery(event.currentTarget);
        var attr_id = component.attr('id').split('-');
        var component_id = attr_id.pop();
        var component_type = attr_id.pop();

        cancel(event);
        if(last_id != component_id) {
            close(event);
        }

        tooltip = jQuery('#tooltip-' + component_id).css({position: 'absolute'}).show();
        if(component_type != 'tooltip') {
            var container = component.closest('.photo, .collage, #photo');
            tooltip_top = container.offset().top + component.position().top - tooltip.height() + 5;
            tooltip_left = container.offset().left + component.position().left;
        }
        tooltip.css({'top': tooltip_top, 'left': tooltip_left});
        if(!component.hasClass('tooltip') && last_id != component_id) {
            tooltip.stop().animate({opacity: 1}, 300);
        } else {
            tooltip.css({opacity: 1});
        }
        last_id = component_id;
    }

    function close(event) {
        if(tooltip) {
            tooltip.stop().animate({opacity: 0}, 250, 'linear', function() { jQuery(this).hide() });
            tooltip = false;
            last_id = false;
        }
    }

    function timer(event) {
        closetimer = window.setTimeout(function() { close(event) }, 100);
    }

    function cancel(event) {
        if(closetimer) {
            window.clearTimeout(closetimer);
            closetimer = null;
        }
    }

    $.fn.enableApprlTooltip = function() {
        this.live('mouseenter', open).live('mouseleave', timer);
        jQuery('.tooltip').live('mouseenter', open).live('mouseleave', timer);
        jQuery(document).click(close);
        jQuery('.tooltip .product-image').hover(
            function(e) {
                jQuery(e.currentTarget).parent().find('.product-meta > a').addClass('hover');
            },
            function(e) {
                jQuery(e.currentTarget).parent().find('.product-meta > a').removeClass('hover');
            });

        return this;
    };

})(jQuery);
