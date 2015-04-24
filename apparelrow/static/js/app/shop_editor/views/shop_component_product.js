App.Views.ShopComponentProduct = App.Views.ShopComponent.extend({

    className: 'col-product-item',
    tagName: 'li',

    template: _.template($('#shop_component_product').html()),

    info: function(e) {
        if(this.model.has('product') && !$(e.target).is('.delete') && !this.$el.is('.ui-draggable-dragging')) {
            // TODO: this.model.get('product') is not a real model
            App.Events.trigger('widget:product:info', new App.Models.Product(this.model.get('product')), true);
            return false;
        }
    },

    render: function() {
        this.$el.html(this.template(this.model.toJSON()));

        // TODO: cannot use backbone events because click event must bind after
        // draggable events
        this.$el.on('click', '.btn-product-info', _.bind(this.info, this));

        return this;
    }

});
