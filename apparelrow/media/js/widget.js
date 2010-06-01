var ApparelRow ={
    host: 'http://localhost:8000',
    initialized: false,
    initStack: 0,
    insert: function(response, ele) {
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
        
        ele.html(html);

        $('.ar-collage, .ar-product', ele).tooltip({
            tipClass: 'ar-tooltip',
            effect: 'slide',
            relative: true,
            delay: 500,
            offset: [30, 0]
        });
    },
    initializers: {
        'look-collage': function(root) {
            var reqUrl = ApparelRow.host + '/widget/look/' + root.attr('id').split('-').pop() + '/collage/?callback=?';

            $.ajax({
                url: reqUrl,
                dataType: 'jsonp',
                success: function(response, statusText) {
                    console.log(statusText);
                    if(response.success)
                        ApparelRow.insert(response, root);
                    else
                        root.remove();
                }
            });
        }
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

