// Sticky v1.0 by Daniel Raftery
// http://thrivingkings.com/sticky
//
// http://twitter.com/ThrivingKings

(function($) {

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
                $('body').append('<div class="sticky-queue top-right"></div>');
            }
        
            // Can it be displayed?
            if(display) {
                // Building and inserting sticky note
                $('.sticky-queue').prepend('<div class="sticky border-top-right" id="' + uniqID + '"></div>');
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
                    $('#' + uniqID).delay(settings['autoclose']).fadeOut(settings['speed']);
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
            $(this).dequeue().fadeOut(settings['speed']);
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
