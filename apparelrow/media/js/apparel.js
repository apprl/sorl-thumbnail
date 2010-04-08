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
    //Hover state for share button
    jQuery('.share').hover(
        function() { jQuery(this).find('ul').show(); }, 
        function() { jQuery(this).find('ul').hide(); }
    );
});


function form_to_ajax(form, callback) {
    jQuery.ajax({
        type: form.method,
        url: form.action,
        data: jQuery(form).serialize(),
        success: function(data, statusText, req) {
            if(!data.success && data.error_message == 'Login required') {
                window.location = data.login_url
                return;
            }
            
            return callback(data, statusText, req)
        },
        dataType: 'json',
    });
    return false;
}