App.Views.Products = Backbone.View.extend({

    el: '#product-list',

    events: {
        'scroll': 'infinite_scroll'
    },

    initialize: function(options) {
        this.filter = options.filter;
        this.filter.on('change', this.update, this);
        this.collection.on('reset', this.render, this);

        this.loading = false;
        this.infinite_scroll();
    },

    infinite_scroll: function() {
        if(!this.loading && (this.$el.scrollTop() / (this.el.scrollHeight - this.$el.height())) > 0.75) {
            this.loading = true;
            this.collection.fetch_next(_.bind(function() { this.loading = false; }, this));
        }
    },

    update: function() {
        this.$el.empty();
        this.collection.fetch({data: this.filter.toJSON(), success: _.bind(function() { this.loading = false; }, this)});
    },

    render: function() {
        this.collection.each(_.bind(function(model) {
            this.$el.append(new App.Views.Product({model: model}).render().el);
        }, this));
    }

});
