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
        if('unset' in options && options.unset) {
            if(!('price' in this.model.attributes) &&
               !('category' in this.model.attributes) &&
               !('subcategory' in this.model.attributes) &&
               !('color' in this.model.attributes) &&
               !('q' in this.model.attributes)) {
                this.$el.hide();
            }
        }
        if(value) {
            this.$el.show();
        }
    }

});
