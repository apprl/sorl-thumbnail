window.App.Models.SearchProduct = Backbone.Model.extend({
    url: '/products',

    defaults: {
        'facet': 'category,color,price'
    },

    initialize: function() {
        this.products = new App.Collections.Products();
    },

    parse: function(response) {
        this.products.reset(response.products);
        delete response.products;

        return response;
    },

    fetch: function(options) {
        options = options || {};
        options.data = options.data || {};
        _.extend(options.data, this.toJSON());

        return this.constructor.__super__.fetch.call(this, options);
    },
});
