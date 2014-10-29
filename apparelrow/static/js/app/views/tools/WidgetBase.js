App.Views.WidgetBase = Backbone.View.extend({

    initialize: function() {
        $('.widget-footer').on('click', '.btn-add-item', _.bind(this.show_product_filter, this));
        App.Events.on('look_edit:product:add', this.hide_product_filter, this);
    },

    show_product_filter: function() {
        $('.col-widget').addClass('visible-md').addClass('visible-lg');
        $('#product-chooser').parent().addClass('visible-xs');
    },

    hide_product_filter: function() {
        $('.col-widget').removeClass('visible-md').removeClass('visible-lg');
        $('#product-chooser').parent().removeClass('visible-xs');
    }
});