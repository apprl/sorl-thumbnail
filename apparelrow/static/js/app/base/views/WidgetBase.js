App.Views.WidgetBase = Backbone.View.extend({

    initialize: function(obj) {
        $('.widget-footer').on('click', '.btn-add-item', _.bind(this.show_product_filter, this));
        $('.widget-footer').on('click', '.btn-touch-menu', _.bind(this.show_touch_menu, this));

        // Header - send model so we can fetch title and publish info - should always be available (set default values otherwise)
        var header = new App.Views.Header({model: obj.model});
        $('#content-container').prepend(header.render().el);

        this.popup_dispatcher = new App.Views.PopupDispatcher();
        this.popup_dispatcher.add('dialog_mobile_menu', new App.Views.DialogHeaderMobile({model:obj.model}));

        App.Events.on('look_edit:product:add', this.hide_product_filter, this);
    },

    show_touch_menu: function() {
        this.popup_dispatcher.show('dialog_mobile_menu');
    },

    show_product_filter: function() {
        $('.widget-footer').css('visibility', 'hidden');
        $('.col-widget').addClass('visible-md').addClass('visible-lg');
        $('#product-chooser').parent().addClass('visible-xs');
        // trigger resize so the product chooser adapts properly
        $(window).trigger('resize');
    },

    hide_product_filter: function() {
        $('.col-widget').removeClass('visible-md').removeClass('visible-lg');
        $('#product-chooser').parent().removeClass('visible-xs');
        $('.widget-footer').css('visibility', '')
        $(window).trigger('resize');
    }
});