var ApparelRow ={
    host: 'http://localhost:8000',
    initialized: false,
    initStack: 0,
    insert: function(response, ele) {
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
            .replace(/(\bsrc=(?:"|')?)(?=\/)/g, function(s, attr) {
                // FIXME: This adds the host name to all local variables. This
                // should be the static host name, not necessarily the same
                // as ApparelRow.host in the future. Also, this could be done
                // on the server
                return attr + ApparelRow.host;
            })
        ;
        
        ele.html(html);

        $('.ar-collage, .ar-product', ele).tooltip({
            tipClass: 'ar-tooltip',
            effect: 'slide',
            relative: true,
            delay: 500,
            offset: [30, 60]
        });
    },
    initializers: {
        'ar-look-collage': function(root) {
            var reqUrl = ApparelRow.host + '/widget/look/' + root.attr('id').split('-').pop() + '/collage/?callback=?';

            $.ajax({
                url: reqUrl,
                dataType: 'jsonp',
                success: function(response, statusText) {
                    if(response.success)
                        ApparelRow.insert(response, root);
                    else
                        root.remove();
                }
            });
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
        
        console.log($('head').html());
                
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

