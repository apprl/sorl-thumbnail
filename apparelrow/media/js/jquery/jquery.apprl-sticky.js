// Sticky v1.0 by Daniel Raftery
// http://thrivingkings.com/sticky
//
// http://twitter.com/ThrivingKings

(function($) {

    var STICKY_OFFSET = 30;

    var settings = {
        'speed': 'slow',
        'duplicates': false,
        'autoclose': 10000,
    };

    var methods = {
        init: function(options, callback) { 
            note = $(this).html();
            if(options) { $.extend(settings, options); }
        
            // Variables
            var display = true;
            var duplicate = 'no';
        
            // Somewhat of a unique ID
            var uniqID = Math.floor(Math.random()*99999);
        
            // Handling duplicate notes and IDs
            $('.sticky-note').each(function() {
                if($(this).html() == note && $(this).is(':visible')) { 
                    duplicate = 'yes';
                    if(!settings['duplicates']) {
                        display = false;
                    }
                }
                if($(this).attr('id') == uniqID) {
                    uniqID = Math.floor(Math.random()*9999999);
                }
            });
        
            // Make sure the sticky queue exists
            if(!$('body').find('.sticky-queue').html()) {
                var offset_container = jQuery('#inner-container').offset().top + STICKY_OFFSET;
                var offset_scroll = $(window).scrollTop();
                var offset = offset_container - offset_scroll;
                var queue = jQuery('<div class="sticky-queue"></div>').css('top', (offset < STICKY_OFFSET ? STICKY_OFFSET : offset));
                $('body').append(queue);
                $(window).scroll(function(event) {
                    var offset_scroll = $(window).scrollTop();
                    var offset = offset_container - (offset_scroll < 0 ? 0 : offset_scroll);
                    queue.css('top', (offset < STICKY_OFFSET ? STICKY_OFFSET : offset));
                });
            }
        
            // Can it be displayed?
            if(display) {
                // Building and inserting sticky note
                $('.sticky-queue').prepend('<div class="sticky" id="' + uniqID + '"></div>');
                $('#' + uniqID).append('<div class="sticky-note" rel="' + uniqID + '">' + note + '</div>');
          
                // Smoother animation
                var height = $('#' + uniqID).height();
                $('#' + uniqID).css('height', height);
          
                $('#' + uniqID).fadeIn(settings['speed']);
                display = true;
            }
        
            // Listeners
            $('.sticky').ready(function() {
                // If 'autoclose' is enabled, set a timer to close the sticky
                if(settings['autoclose']) {
                    var elem = $('#' + uniqID);
                    elem.data('timer', setTimeout(function() { elem.fadeOut(settings['speed']); }, settings['autoclose']));
                }
            });

            // Callback data
            var response = {
                'id': uniqID,
                'duplicate': duplicate,
                'displayed': display
            }

            // Callback function?
            if(callback) { 
                callback(response);
            } else {
                return response;
            }

        },
        close: function() {
            clearTimeout($(this).data('timer'));
            $(this).fadeOut(settings['speed']);
        },
        stay: function() {
            clearTimeout($(this).data('timer'));
        },
        extend: function() {
            var elem = $(this);
            clearTimeout(elem.data('timer'));
            elem.data('timer', setTimeout(function() { elem.fadeOut(settings['speed']); }, settings['autoclose']));
        }
    };

    $.fn.sticky = function(method) {
        if(methods[method]) {
            return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if(typeof method === 'object' || !method) {
            return methods.init.apply(this, arguments);
        } else {
            $.error('Method ' + method + ' does not exist on jQuery.sticky');
        }    
    };

})(jQuery);
