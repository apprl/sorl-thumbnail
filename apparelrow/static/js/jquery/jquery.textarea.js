(function($) {

    var isLoading = false;
    var isActive = false;
    var selector = false;
    var element = false;

    function disableEditable() {
        element.attr('contenteditable', 'false');
    }

    function enableEditable() {
        element.attr('contenteditable', 'true');
    }

    function showElement() {
        element.css({opacity: 0.5, cursor: 'pointer'});
    }

    function resetElement() {
        element.css({opacity: 1, cursor: 'default'});
    }

    $.fn.enableEditable = function(url) {
        element = $(this);
        selector = element.selector;

        enableEditable();

        $(document)
            .on('mouseenter', selector, function() {
                if(!isActive) {
                    showElement();
                }
            })
            .on('mouseleave', selector, function() {
                if(!isActive) {
                    resetElement();
                }
            })
            .on('click focusin', selector, function() {
                if (!isLoading) {
                    isActive = true;
                    resetElement();
                }
            })
            .on('focusout', selector, function() {
                isLoading = true;

                elementString = element.html().replace(/<div>/gi,'').replace(/<\/div>/gi,'<br>');;

                showElement();
                disableEditable();
                $.post(url, {description: elementString}, function(html) {
                    element.html(html);
                    enableEditable();
                    resetElement();
                    isActive = false;
                    isLoading = false;
                })
            });

        return this;
    };

})(jQuery);
