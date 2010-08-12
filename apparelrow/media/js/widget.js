/*
 * ApparelRow.com Widget Embedment
 */

var ApparelRow = {
    host: 'http://localhost:8000',
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
                return attr + ApparelRow.host;
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
        
        
        
        // Make hotspots/collage products link to ApparelRow
        $('.ar-product, .ar-hotspot', node)
            .click(function() {
                var id = this.id.split('-').pop();
                location.href = ApparelRow.host + '/products/' + id;
                return false; 
             } )
            .addClass('ar-link')
        ;
        
        // Point tooltip link to ApparelRow. FIXME: Could this be done in the server?
        $('.ar-tooltip > a').each(function(i, e) {
            var id = jQuery(e).closest('.ar-tooltip').prev().attr('id').split('-').pop();
            e.href = ApparelRow.host + '/products/' + id;
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
                ApparelRow.insert(response, node);
            else
                root.remove();        
        };
        
        $.ajax({
            url: ApparelRow.host + path + '?callback=?',
            dataType: 'jsonp',
            success: callback
        });
    },
    initializers: {
        'ar-look-collage': function(node) {
            ApparelRow.request('/widget/look/' + node.attr('id').split('-').pop() + '/collage/', node);
        },
        'ar-look-photo': function(node) {
            ApparelRow.request('/widget/look/' + node.attr('id').split('-').pop() + '/photo/', node);
        }
    },
    initialize: function() {
        if(ApparelRow.initialized)
            return;
        
        ApparelRow.initialized = true;
        
        $('<link/>')
            .attr('href', ApparelRow.host + '/media/styles/widget.css')
            .attr('rel', 'stylesheet')
            .attr('type', 'text/css')
            .appendTo('head');

        $('.apparelrow').each(function(idx, e) {
            var element = $(e);
            for(var cls in ApparelRow.initializers) {
                if(element.hasClass(cls))
                    ApparelRow.initializers[cls](element);
            }
        });
    }
};

$(document).ready(function() { ApparelRow.initialize() });
if(document && document.getElementById && document.getElementById('__ar_widget__'))
    ApparelRow.initialize();

