(function($) {

    var isActive = false,
        form = false,
        description = false,
        element = false;

    function toggleActive() {
        if (isActive) {
            element.show();
            form.hide();
            description.show();
        } else {
            element.hide();
            form.show();
            description.hide();
        }
        isActive = !isActive;
    }

    $.fn.enableEditable = function() {
        element = $(this),
        form = $('#description-form'),
        description = $('.description');

        form.on('click', '.btn-save-description', function(e) {
            e.preventDefault();
            $.post(form.attr('action'), {description: form.find('textarea').val()}, function(html) {
                description.html(html);
                toggleActive();
            });
        });

        form.on('click', '.btn-cancel-description', function(e) {
            e.preventDefault();
            toggleActive();
        });

        $(document).on('click', element.selector, toggleActive);

        return this;
    };

})(jQuery);
