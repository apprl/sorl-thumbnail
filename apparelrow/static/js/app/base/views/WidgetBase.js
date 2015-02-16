App.Views.WidgetBase = Backbone.View.extend({

    initialize: function(obj) {
        // Header - send model so we can fetch title and publish info - should always be available (set default values otherwise)
        var header = new App.Views.Header({model: obj.model});
        $('#content-container').prepend(header.render().el);
        $('.close-product-chooser').on('click', _.bind(this.hide_product_filter, this));

        this.popup_dispatcher = new App.Views.PopupDispatcher();
        this.popup_dispatcher.add('dialog_mobile_menu', new App.Views.DialogHeaderMobile({model:obj.model}));

        App.Events.on('widget:product:add', this.hide_product_filter, this);
        this.disable_footer();
    },

    init_footer: function() {
        $('.widget-footer').on('click', '.btn-add-item', _.bind(this.show_product_filter, this)).
            on('click', '.btn-touch-menu', _.bind(this.show_touch_menu, this)).
            css({'visibility': 'visible', 'height': ''});
    },

    disable_footer: function() {
        $('.widget-footer').css({'visibility': 'hidden', 'height': '0px'});
    },

    show_touch_menu: function() {
        this.popup_dispatcher.show('dialog_mobile_menu');
    },

    show_product_filter: function() {
        $('.widget-footer').css('visibility', 'hidden');
        $('.col-widget').addClass('visible-md').addClass('visible-lg');
        $('#product-chooser').parent().addClass('visible-xs').addClass('visible-sm');
        $('#startsplash').hide();
        // trigger resize so the product chooser adapts properly
        $(window).trigger('resize');
    },

    hide_product_filter: function() {
        $('.col-widget').removeClass('visible-md').removeClass('visible-lg');
        $('#product-chooser').parent().removeClass('visible-xs').removeClass('visible-sm');
        $('.widget-footer').css('visibility', '')
        $(window).trigger('resize');
    }
});