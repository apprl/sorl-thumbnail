function increase_counts(counts, new_count) {
    // For each element, set to new_count if available, otherwise increase the current count with 1
    counts.each(function() {
        $(this)
            .hide()
            .html(new_count ? new_count : parseInt($(this).html()) + 1)
            .fadeIn()
            ;
    });
}
jQuery(document).ready(function() {
    // Make all "apparel rows" scrollables
    jQuery('.row').scrollable().end();


    // Adding comments to jquery-tmpl, syntax: {{#}}comment{{/#}} Note: the "" are important
    jQuery.tmplcmd['#'] = {
        prefix: '/*',
        suffix: '*/'
    }
    var likeContainers = 'body.look #content, body.product .product-image';
    jQuery(likeContainers).children('form').hide();
    jQuery(likeContainers).hover(
        function() { jQuery(this).find('form').fadeIn(); },
        function() { jQuery(this).find('form').fadeOut(); }
    );
    jQuery(likeContainers).children('form').hyperSubmit({
        success: function(response, statusText, req, form) {
            // Match "/model/slug/like"
            if(/^\/(\w+)\/([\w-]+)\/like/.test(form.attr('action'))) {
                increase_counts(jQuery('#like-' + RegExp.$1 + '-' + RegExp.$2 + ' > span.count'), response.score.score);
            }
        },
    });
    // Comments posting
    var comment_area = jQuery('#comments-and-links textarea');
    if(comment_area.val() == '')
        jQuery('#comments-and-links button').hide();
    comment_area
        .focus(function() { jQuery('#comments-and-links button').show() })
        .blur(function() { if(jQuery(this).val() == '') jQuery('#comments-and-links button').hide() })
        .autogrow();
    jQuery('#comments-and-links form').hyperSubmit({
        success: function(data, statusText, req) {
            comment_area.val('');
            jQuery('#comments-and-links button').hide();
            jQuery(data.html).hide().appendTo('ul#comments').slideDown('fast');
            increase_counts(jQuery('a.comments > span.count'));
            return false;
        },
    });
    //Hover state for share button
    jQuery('.share').hover(
        function() { jQuery(this).find('ul').show(); }, 
        function() { jQuery(this).find('ul').hide(); }
    );
    jQuery('.share').click(function() { jQuery(this).find('ul').toggle(); return false; })
    
    jQuery('ul.hover-menu li[class!=active]')
        .live('mouseenter', function(e) { 
            jQuery(this).addClass('hover'); 
            return true;
        } )
        .live('mouseleave', function(e) { 
            jQuery(this).removeClass('hover');
            return true; 
        } )
    ;
});


function makeProductTooltip(selector) {
    var q = (typeof selector == 'string')
        ? jQuery(selector)
        : selector;
    
    q.tooltip({
        effect: 'slide',
        relative: true,
        delay: 500,
        offset: [30, 60]
    });
}
