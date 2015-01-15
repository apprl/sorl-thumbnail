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

        this.$product_list_empty = this.$el.parent().find('#product-list-empty');
        this.$product_list_empty.on('click', '.btn-reset', _.bind(this.reset, this));

        this.$product_list_unauthenticated = this.$el.parent().find('#product-list-unauthenticated');
        App.Events.on('product_list:unauthenticated', _.bind(this.handle_unauthenticated, this));
    },

    handle_unauthenticated: function(display) {
        this.display_unauthenticated = display;
        this.render();
    },

    reset: function() {
        this.filter.reset();
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
        if(this.display_unauthenticated) {
            this.$el.hide();
            this.$product_list_unauthenticated.show();
            this.$product_list_empty.hide();
        } else if(this.collection.length == 0) {
            this.$el.hide();
            this.$product_list_unauthenticated.hide();
            this.$product_list_empty.show();
        } else {
            this.$el.show();
            this.$product_list_unauthenticated.hide();
            this.$product_list_empty.hide();
            this.collection.each(_.bind(function(model) {
                this.$el.append(new App.Views.Product({model: model}).render().el);
            }, this));
        }
    }

});
