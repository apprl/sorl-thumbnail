var ApparelRow ={
    host: 'http://localhost:8000',
    initialized: false,
    initStack: 0,
    insert: function(response) {
        // FIXME: Backtracking would be nice here so we could have one rather  
        // than two replace statements
        
        // FIXME: This prepends 'ar-' to all class names
        // maybe there's a case for doing this on the server, or just always 
        // have the classes with this prefix?
        
        console.log('callback');
        
        var html = response.html.replace(/class="(.+?)"/g, function(s) {
                var c = RegExp.$1.replace(/(.+?)(?:\s|$)/g, function(c) {
                    return 'ar-' + c;
                });
                
                return 'class="' + c + '"';
            });
        
        $('#' + response.domid).replaceWith(html)
        
        if(--ApparelRow.initStack == 0)
            ApparelRow.completed();
    },
    initializers: {
        'look-collage': function(root) {
            var rootId = root.attr('id');
            var reqUrl = ApparelRow.host + '/widget/look/' + rootId.split('-').pop() + '/collage/?domid=' + rootId + '&callback=?';

            $.ajax({
                url: reqUrl,
                type: 'HEAD', 
                success: function(response, status, request) {
                    if(request.statusText == 'OK') {
                        ApparelRow.initStack++;            
                        $.getJSON(reqUrl);
                    }
                }
            })
        }
    },
    completed: function() {
        $('.ar-collage, .ar-product').tooltip({
            tipClass: 'ar-tooltip',
            effect: 'slide',
            relative: true,
            delay: 500,
            offset: [30, 0]
        });
    }
};

$(document).ready(function() {
    if(ApparelRow.initialized == false) {
        ApparelRow.initialized = true;
        
        $('.apparelrow').each(function(idx, e) {
            var element = $(e);
            for(var cls in ApparelRow.initializers) {
                if(element.hasClass(cls))
                    ApparelRow.initializers[cls](element);
            }
        });
    }
});

document.writeln('<script type="text/javascript" src="' + ApparelRow.host + '/media/js/jquery.tools.min.js"></' + 'script>');
document.writeln('<link rel="stylesheet" type="text/css" href="' + ApparelRow.host + '/media/css/widget.css"/>');

