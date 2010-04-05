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
            console.log(data);
                jQuery('span.likes > span').html(data.score.score);
            },
            dataType: 'json',
        });
        return false;
    });
});
