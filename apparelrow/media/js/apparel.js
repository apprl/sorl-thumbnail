jQuery(document).ready(function() {
    var likeContainers = 'body.look .collage, body.product .product-image';
    jQuery(likeContainers).children('form').hide();
    jQuery(likeContainers).hover(
        function() { jQuery(this).find('form').fadeIn(); },
        function() { jQuery(this).find('form').fadeOut(); }
    );
    jQuery(likeContainers).children('form').submit(function() {
        jQuery.ajax({
            type: this.method,
            url: this.action,
            data: jQuery(this).serialize(),
            success: function(data, statusText, req) { 
                var likes = jQuery('span.likes > span');
                //likes.width(likes.width()).hide().html(data.score.score).fadeIn();
                likes.hide().html(data.score.score).fadeIn();
            },
            dataType: 'json',
        });
        return false;
    });
});
