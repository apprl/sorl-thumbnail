window.App.Models.SearchProduct = Backbone.Model.extend({
    url: '/products',

    defaults: {
        'facet': 'category,color,price'
    },

    initialize: function() {
        this.products = new App.Collections.Products();

        this.facet = {
            'color': new App.Collections.Facets(),
            'category': new App.Collections.Facets(),
            'price': new App.Collections.Facets(),
        };
    },

    parse: function(response) {
        this.products.reset(response.products);
        delete response.products;

        this.facet['category'].reset(response.facet_category);
        delete response.facet_manufacturer;
        delete response.facet_category;
        delete response.facet_color;
        delete response.facet_price;

        return response;
    },

    fetch: function(options) {
        options = options || {};
        options.data = options.data || {};
        _.extend(options.data, this.toJSON());

        return this.constructor.__super__.fetch.call(this, options);
    },
});
