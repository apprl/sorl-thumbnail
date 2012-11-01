/**
 * jquery.scrollable.js
 * Copyright (c) 2012 Joel Bohman (http://jbohman.com/)
 * Licensed under the MIT License (http://www.opensource.org/licenses/mit-license.php)
 */
(function(jQuery){
    jQuery.fn.simple_scrollable = function(distance, duration) {
        if(typeof distance === 'undefined') {
            distance = this.find('ul li').outerWidth(true);
        }

        if(typeof duration === 'undefined') {
            duration = 700;
        }

        var next_button = this.siblings('.next');
        var prev_button = this.siblings('.prev');
        var ul_list = this.find('ul');

        var display_width = this.width();
        var total_width = -display_width;
        this.find('li').each(function(index, element) {
            if(index == 0) {
                total_width += jQuery(this).outerWidth(false);
            } else {
                total_width += jQuery(this).outerWidth(true);
            }
        });

        if(total_width < 0) {
            next_button.addClass('disabled');
        }

        next_button.click(function(event) {
            var left_offset = ul_list.position().left;
            var dx = distance;
            if(Math.abs(left_offset - distance) >= total_width) {
                dx = total_width - Math.abs(left_offset);
                jQuery(this).addClass('disabled');
            }
            prev_button.removeClass('disabled');
            ul_list.animate({left: '-=' + dx}, {duration: duration, queue: false});
        });

        prev_button.click(function(event) {
            var left_offset = ul_list.position().left;
            var dx = distance;
            if(left_offset + distance >= 0) {
                dx = Math.abs(left_offset);
                jQuery(this).addClass('disabled');
            }
            next_button.removeClass('disabled');
            ul_list.animate({left: '+=' + dx}, {duration: duration, queue: false});
        }).addClass('disabled');

        return this;
    };
})(jQuery);
