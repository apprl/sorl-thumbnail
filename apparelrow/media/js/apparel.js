jQuery(document).ready(function() {
    var likeContainers = 'body.look .collage, body.product .product-image';
    jQuery(likeContainers).children('form').hide();
    jQuery(likeContainers).hover(
        function() { jQuery(this).find('form').fadeIn(); },
        function() { jQuery(this).find('form').fadeOut(); }
    );
    jQuery(likeContainers).children('form').submit(function() {
        return form_to_ajax(this, function(data, statusText, req) { 
            var likes = jQuery('span.likes > span');
            likes.hide().html(data.score.score).fadeIn();
        });
    });
});


function form_to_ajax(form, e, callback, error_callback) {
    query  = jQuery(form).serialize();
    if(e && e.originalEvent && e.originalEvent.explicitOriginalTarget) {
        target = e.originalEvent.explicitOriginalTarget;
    
        if("name" in target && "value" in target )
            // FIXME: Also check that the query string query also doesn't contain target.name
            query += '&' + escape(target.name) + '=' + escape(target.value);
    }
    
    jQuery.ajax({
        type: form.method,
        url: form.action,
        data: query,
        success: function(data, statusText, req) {
            if(!data.success) {
                if('location' in data) {
                    window.location = data.location
                    return;
                }
                
                if(typeof error_callback == 'function')
                    return error_callback(data, req);
                
                alert('Error in AJAX call:\n' + data.error_message);
                return;
            }
            
            return callback(data, statusText, req)
        },
        dataType: 'json',
    });
    return false;
}

