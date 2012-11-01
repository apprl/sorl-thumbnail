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

        // Tooltip is either component or next to component
        tooltip = component;
        if(!component.hasClass('tooltip')) {
            tooltip = component.next('.tooltip');
        }
        tooltip.show();
        if(component_type != 'tooltip') {
            var padding = 15;
            var container = component.closest('div');
            var container_w = container.width();
            var container_h = container.height();
            var component_p = component.position();
            var component_h = component.height();
            var component_w = component.width();
            var tooltip_w = tooltip.outerWidth();
            var tooltip_h = tooltip.outerHeight();

            tooltip_top = component_p.top + Math.floor(component_h / 2);
            tooltip_left = component_p.left + Math.floor(component_w / 2) - Math.floor(tooltip_w / 2);

            var tooltip_arrow = tooltip.find('.tooltip-arrow').css({left: 135});
            if(tooltip_h + padding < tooltip_top) {
                tooltip_arrow.addClass('tooltip-arrow-bottom');
                tooltip_top -= tooltip_h + padding;
            } else {
                tooltip_arrow.addClass('tooltip-arrow-top');
                tooltip_top += padding;
            }

            if(tooltip_left < 5) {
                tooltip_arrow.css('left', 135 - (5 - tooltip_left));
                tooltip_left = 5;
            } else if(tooltip_left + tooltip_w + 5 > container_w) {
                tooltip_arrow.css('left', 135 + (tooltip_w - (container_w - tooltip_left)) + 5);
                tooltip_left -= (tooltip_w - (container_w - tooltip_left)) + 5;
            }
        }

        tooltip.css({'top': tooltip_top, 'left': tooltip_left});
        if(!component.hasClass('tooltip') && last_id != component_id) {
            tooltip.stop().animate({opacity: 1}, 300);
        } else {
            //tooltip.css({opacity: 1});
        }
        last_id = component_id;
    }

    function close(event) {
        if(tooltip) {
            tooltip.stop().animate({opacity: 0}, 250, 'linear', function() { jQuery(this).hide(); });
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
