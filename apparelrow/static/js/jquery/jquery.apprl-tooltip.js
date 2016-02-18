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

            // Find start of first non-transparent pixel by taking 1xH sample
            // in the middle of the image
            var start = 0;
            //var image = component.find('img');
            //if(image.length > 0) {
                //start = image.data('loaded');
                //if(typeof start === 'undefined') {
                    //var first_pixel = 0;
                    //var canvas = document.createElement('canvas');
                    //canvas.width = component_w;
                    //canvas.height = component_h;
                    //if(!!(canvas.getContext && canvas.getContext('2d'))) {
                        //var ctx = canvas.getContext('2d');
                        //ctx.drawImage(image.get(0), 0, 0, component_w, component_h);
                        //var image_data = ctx.getImageData(component_w/2, 0, 1, component_h);
                        //var pixels = image_data.data;
                        //for (var i = 0, n = pixels.length; i < n; i += 4) {
                            //if(!pixels[i+3] == 0) {
                                //first_pixel = i / 4;
                                //break;
                            //}
                        //}
                    //}
                    //image.data('loaded', first_pixel);
                    //start = first_pixel;
                //}
            //}

            // Modified on Feb 18 to account for new close button space (+20)
            tooltip_top = component_p.top + start + Math.floor((component_h - start) / 3);
            tooltip_left = component_p.left + Math.floor(component_w / 2) - Math.floor(tooltip_w / 2);

            var tooltip_arrow = tooltip.find('.tooltip-arrow').css({left: 135});
            if(tooltip_h + padding < tooltip_top) {
                tooltip_arrow.addClass('tooltip-arrow-bottom');
                tooltip_top -= tooltip_h + padding;
            } else {
                tooltip_arrow.addClass('tooltip-arrow-top');
                tooltip_top += padding;
            }

            if (tooltip_h + padding + tooltip_top > container_h) {
                tooltip_top -= tooltip_h + padding + tooltip_top - container_h + 30;
                tooltip_arrow.removeClass('tooltip-arrow-top').addClass('tooltip-arrow-bottom')
            }

            if(tooltip_left < 5) {
                tooltip_arrow.css('left', 135 - (5 - tooltip_left));
                tooltip_left = 5;
            } else if(tooltip_left + tooltip_w + 5 > container_w) {
                // Modified on Feb 18 to account for new close button space
                tooltip_arrow.css('left', 135 + (tooltip_w - (container_w - tooltip_left)) + 20);
                tooltip_left -= (tooltip_w - (container_w - tooltip_left)) + 20;
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

    $.fn.enableApprlTooltip = function(selector) {
        jQuery(document).on({'touchstart': function(event) {event.preventDefault(); open(event); }}, selector)
        jQuery(document).on({'mouseenter': open, 'mouseleave': timer}, selector);
        jQuery(document).on({'mouseenter': open, 'mouseleave': timer}, '.tooltip');
        jQuery(document).on('click', close);
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
