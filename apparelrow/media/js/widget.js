var ApparelRow = {
    initialized: false,
    insert: function(response) {
        $('#' + response.domid).replaceWith(response.html)
    },
    initializers: {
        'look-collage': function(root) {
            console.log('Found element', root);
            var id = root.attr('id').split('-').pop();
            
            // NOTE: the location object is set to whatever URL that served the page including this script, not the script itself
            $.getJSON('http://localhost:8000/widget/look/' + id + '/collage/?domid=' + root.attr('id') + '&callback=?');
        }
    },
}

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
