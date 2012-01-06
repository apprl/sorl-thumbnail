/*
 * Apparelrow.com Widget Embedment
 */

var Apparelrow = {
    host: __ar_host__ || 'http://www.apparelrow.com',
    initialized: false,
    initStack: 0,
    insert: function(response, node) {
        // FIXME: Backtracking would be nice here so we could have one rather  
        // than two replace statements
        
        var html = response.html
            .replace(/class="(.+?)"/g, function(s, clsname) {
                // FIXME: This prepends 'ar-' to all class names
                // maybe there's a case for doing this on the server, or just always 
                // have the classes with this prefix?
                return 'class="'
                    + clsname.replace(/(.+?)(?:\s+|$)/g, function(c) { return 'ar-' + c; } )
                    + '"'
                ;
            })
            .replace(/((?:\b(?:src|href)=(?:"|')?)|(?:\:\s+url\((?:"|')))(?=\/)/g, function(s, attr) {
                // FIXME: This adds the host name to all html attributes src or href or
                // inline css attributes url( whos value starts with /
                return attr + Apparelrow.host;
            })
        ;
        
        node.html('<div id="ar-wrapper">' + html + '</div>');
        
        $('.ar-collage, .ar-product', node).tooltip({
            tipClass: 'ar-tooltip',
            effect: 'slide',
            relative: true,
            delay: 500,
            offset: [15, 0]
        });
        
        // Hide hotspots and only show them on mouseover
        $('.ar-hotspot').hide();
        $('.ar-look-photo').hover(
              function(e) { jQuery('.ar-hotspot', this).fadeIn() }
            , function(e) { 
                if(!e.originalTarget || e.originalTarget.id != this.id)
                    return true;
                jQuery('.ar-hotspot', this).fadeOut();
            }
        );
    },
    request: function(path, node, callback) {
        callback = callback || function(response, statusText) {
            if(response.success) 
                Apparelrow.insert(response, node);
            else
                node.remove();        
        };
        
        $.ajax({
            url: Apparelrow.host + path + '?callback=?',
            dataType: 'jsonp',
            success: callback
        });
    },
    initializers: {
        'ar-look-collage': function(node) {
            Apparelrow.request('/widget/look/' + node.attr('id').split('-').pop() + '/collage/', node);
        },
        'ar-look-photo': function(node) {
            Apparelrow.request('/widget/look/' + node.attr('id').split('-').pop() + '/photo/', node);
        }
    },
    initialize: function() {
        if(Apparelrow.initialized)
            return;
        
        Apparelrow.initialized = true;
        
        $('<link/>')
            .attr('href', Apparelrow.host + '/media/styles/widget.css')
            .attr('rel', 'stylesheet')
            .attr('type', 'text/css')
            .appendTo('head');

        $('.apparelrow').each(function(idx, e) {
            var element = $(e);
            for(var cls in Apparelrow.initializers) {
                if(element.hasClass(cls))
                    Apparelrow.initializers[cls](element);
            }
        });
    }
};

$(document).ready(function() { Apparelrow.initialize() });
if(document && document.getElementById && document.getElementById('__ar_widget__'))
    Apparelrow.initialize();

