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
            var container = component.closest('div');
            var container_o = {top: 0, left: 0};
            if(container.has(tooltip).length == 0) {
              container_o = container.offset();
            }
            var container_w = container.width();
            var container_h = container.height();
            var component_p = component.position();
            var component_h = component.height();
            var tooltip_w = tooltip.outerWidth();
            var tooltip_h = tooltip.outerHeight();

            if(component_p.top >= tooltip_h) {
                tooltip_top = container_o.top + component_p.top - tooltip_h;
            } else if(component_h + tooltip_h >= container_h) {
                tooltip_top = container_o.top + component_p.top + (component_h / 2);
            } else {
                tooltip_top = container_o.top + component_p.top + component_h;
            }

            if((tooltip_top + tooltip_h - container_o.top) >= container_h) {
                tooltip_top -= (tooltip_top + tooltip_h - container_o.top) - container_h;
            }

            if(component_p.left < 0 || tooltip_w >= container_w) {
                tooltip_left = container_o.left + 1;
            } else if(component_p.left + tooltip_w >= container_w) {
                tooltip_left = container_o.left + component_p.left - ((component_p.left + tooltip_w) - container_w);
            } else {
                tooltip_left = container_o.left + component_p.left;
            }
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
