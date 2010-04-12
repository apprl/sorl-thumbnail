jQuery(document).ready(function() {
    var likeContainers = 'body.look .collage, body.product .product-image';
    jQuery(likeContainers).children('form').hide();
    jQuery(likeContainers).hover(
        function() { jQuery(this).find('form').fadeIn(); },
        function() { jQuery(this).find('form').fadeOut(); }
    );
    jQuery(likeContainers).children('form').hyperSubmit({
        success: function(response, statusText, req, form) {
            // Match "/model/slug/like"
            if(/^\/(\w+)\/([\w-]+)\/like/.test(form.attr('action'))) {
                jQuery('#like-' + RegExp.$1 + '-' + RegExp.$2 + ' > span.count')
                    .hide()
                    .html(response.score.score)
                    .fadeIn();
            }
        },
    });
    // Comments posting
    if(jQuery('#comments-and-links textarea').val() == '') { jQuery('#comments-and-links button').hide() }
    jQuery('#comments-and-links textarea').focus(function() { jQuery('#comments-and-links button').show() });
    jQuery('#comments-and-links textarea').blur(function() { if(jQuery(this).val() == '' ) { jQuery('#comments-and-links button').hide() } });
//    jQuery('#comments textarea').autogrow();
    jQuery('#comments-and-links form').hyperSubmit({
        success: function(data, statusText, req) {
            jQuery('#comments-and-links textarea').val('');
            jQuery('#comments-and-links button').hide();
            jQuery(data.html).hide().appendTo('ul#comments').slideDown('fast');
            var count = jQuery('a.comments > span.count');
            count.html(parseInt(count.html()) + 1);
            return false;
        },
    });
    //Hover state for share button
    jQuery('.share').hover(
        function() { jQuery(this).find('ul').show(); }, 
        function() { jQuery(this).find('ul').hide(); }
    );
});

//
//function form_to_ajax(form, callback, error_callback, e) {
//    query  = jQuery(form).serialize();
//    if(e && e.originalEvent && e.originalEvent.explicitOriginalTarget) {
//        target = e.originalEvent.explicitOriginalTarget;
//    
//        if("name" in target && "value" in target )
//            // FIXME: Also check that the query string query also doesn't contain target.name
//            query += '&' + escape(target.name) + '=' + escape(target.value);
//    }
//    
//    jQuery.ajax({
//        type: form.method,
//        url: form.action,
//        data: query,
//        success: function(data, statusText, req) {
//            if(!data.success) {
//                if('location' in data) {
//                    window.location = data.location
//                    return;
//                }
//                
//                if(typeof error_callback == 'function')
//                    return error_callback(data, req);
//                
//                alert('Error in AJAX call:\n' + data.error_message);
//                return;
//            }
//            
//            return callback(data, statusText, req)
//        },
//        dataType: 'json',
//    });
//    return false;
//}
//
