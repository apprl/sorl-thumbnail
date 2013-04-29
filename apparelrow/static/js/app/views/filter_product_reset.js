App.Views.FilterProductReset = Backbone.View.extend({

    el: '.btn-product-reset',

    events: {
        'click': 'product_reset'
    },

    initialize: function() {
        this.model.on('change:category', this.show, this);
        this.model.on('change:subcategory', this.show, this);
        this.model.on('change:color', this.show, this);
        this.model.on('change:price', this.show, this);
        this.model.on('change:q', this.show, this);
    },

    product_reset: function(e) {
        App.Events.trigger('product:reset');
        this.$el.hide();

        e.preventDefault();
    },

    show: function(model, value, options) {
        if(value) {
            this.$el.show();
        }
    }

});
