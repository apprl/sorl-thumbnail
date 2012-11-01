/**
 * jquery.hypersubmit.js
 * Copyright (c) 2010 Hansson & Larsson Internet AB (http://hanssonlarsson.se/)
 * Licensed under the MIT License (http://www.opensource.org/licenses/mit-license.php)
 *
 * @author Linus G Thiel
 *
 * @projectDescription  jQuery plugin for making elements stick to the top of the viewport as the page is scrolled
 *
 * @version 0.1.1
 *
 * @requires jquery.js (tested with 1.4.2)
 *
 * @param success          function - function to execute at success
 *                                      default: logs if console.log is available
 * @param error            function - function to execute at error
 *                                      default: logs if console.log is available
 * @param follow_redirect  boolean  - if true, redirects in error responses will be followed
 *                                      default: true
 *
 * Usage:
 * $('form').hyperSubmit(options);
 *
 * */
(function($) {
    // Define an empty console.log if it's not available
    if(!'console' in window)
        window.console = { log: function() {} };
    
    $.hyperSubmit = $.hyperSubmit || {
        version: '0.1.2',
        defaults: {
            success: function(data, textStatus, req) { console.log("success in form submit, ", data, textStatus, req) },
            error: function(req, textStatus, errorThrown) { console.log("error in form submit, ", req, textStatus, errorThrown) },
            dataType: 'json',
            follow_redirect: true
        }
    };
    $.fn.hyperSubmit = $.fn.hyperSubmit || function(options) {
        var config = $.extend({}, $.hyperSubmit.defaults, options);
        return this.each(function() {
            if(this.tagName.toLowerCase() != 'form')
                return true;
            
            var $this = $(this);
            $this.submit(function(e) {
                var formData = $this.serializeArray();
                if(e.originalEvent && e.originalEvent.explicitOriginalTarget) {
                    var target = e.originalEvent.explicitOriginalTarget;
                    if('name' in target && 'value' in target) {
                        // Only add the value if there is no parameter of the same name
                        if($.grep(formData, function(obj, i) { return target.name in obj }).length == 0) {
                            formData.push({ 'name': target.name, 'value': target.value });
                        }
                    }
                }
                
                var params = $.extend({}, config, {
                    type: this.method,
                    url: this.action,
                    data: $.param(formData),
                    success: function(response, statusText, req) {
                        if(!response.success) {
                            if(config.follow_redirect && 'location' in response) {
                                window.location = response.location;
                                return;
                            }
                            if(typeof config.error == 'function')
                                return config.error(response, req);
                            
                            console.log('Unhandled error in ajax call', response.error_message);
                            return;
                        }
                        return config.success(response, statusText, req, $this);
                    },
                    error: function(response, statusText, error) {
                        return config.error(response, statusText, error, $this);
                    }
                });
                $.ajax(params);
                return false;
            });
        });
    };
})(jQuery);
