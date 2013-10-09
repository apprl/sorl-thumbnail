/**
 * Infinite scroll
 * Automatically scrolls one page
 * To keep auto-scrolling after first page, set $(window).data('dont-scroll', false)
 *
 * To reset, set $(window).data('first-scroll', true)
 * */

window.resetInfiniteScroll = function() {
    var $window = $(window);
    $window.data('first-scroll', true);
    $window.data('dont-scroll', false);
};

window.infiniteScroll = function infiniteScroll(callback) {
    var $window = $(window),
        $document = $(document),
        lastOffset = $window.scrollTop(),
        loading = false;

    function bottomDistance() {
        return $document.height() - $window.scrollTop();
    }

    // Keep track of the first auto-scroll
    // Do not infinite scroll without a click
    $window.data('first-scroll', false);
    $window.data('dont-scroll', true);

    $window.on('scroll', function() {
        if($window.data('dont-scroll')) {
            return;
        }

        var offset = $window.scrollTop(),
            height = $window.height();

        if(!loading && bottomDistance() < 2.5 * height && offset > lastOffset) {
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
};
