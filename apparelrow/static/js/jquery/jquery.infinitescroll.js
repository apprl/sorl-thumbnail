/**
 * Infinite scroll
 * Automatically scrolls one page
 * To keep auto-scrolling after first page, set $(window).data('dont-scroll', false)
 *
 * To reset, set $(window).data('first-scroll', true)
 * */

window.infiniteScroll = function infiniteScroll(callback) {
    var $window = jQuery(window),
        $document = jQuery(document),
        lastOffset = $window.scrollTop(),
        loading = false;

    function bottomDistance() {
        return $document.height() - $window.scrollTop();
    }

    // Keep track of the first auto-scroll
    $window.data('first-scroll', true);

    $window.bind('scroll', function() {
        if($window.data('dont-scroll'))
            return;

        var offset = $window.scrollTop(),
            height = $window.height();

        if(!loading && bottomDistance() < 2 * height && offset > lastOffset) {
            if($window.data('first-scroll')) {
                // Just auto-scroll one page until user clicks "load more"
                $window.data('dont-scroll', true);
                $window.data('first-scroll', false);
            }

            loading = true;
            callback(function() {
                loading = false;
            });
        }

        // Store offset to see scroll direction
        lastOffset = offset;
    });
}
