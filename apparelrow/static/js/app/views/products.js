App.Views.Products = Backbone.View.extend({

    el: '#product-list',

    initialize: function(options) {
        this.collection.on('reset', this.render, this);
    },

    render: function() {
        this.$el.empty();
        this.collection.each(_.bind(function(model) {
            this.$el.append(new App.Views.Product({model: model}).render().el);
        }, this));
    }

});
