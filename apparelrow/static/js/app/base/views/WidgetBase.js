App.Views.WidgetBase = Backbone.View.extend({

    initialize: function() {
        $('.widget-footer').on('click', '.btn-add-item', _.bind(this.show_product_filter, this));
        App.Events.on('look_edit:product:add', this.hide_product_filter, this);
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
    }
});