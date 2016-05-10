window.App.Models.FacetContainer = Backbone.Model.extend({
    url: '/products',

    defaults: {
        'facet': 'manufacturer,category,color,price,store'
    },

    initialize: function() {
        this.manufacturer = new App.Collections.Facets(),
        this.color = new App.Collections.Facets(),
        this.category = new App.Collections.Facets(),
        this.price = new App.Collections.Facets(),
        this.store = new App.Collections.Facets()
    },

    parse: function(response) {
        this.manufacturer.reset(response.manufacturer);
        this.category.reset(response.category);
        this.color.reset(response.color);
        this.price.reset(response.price);
        this.store.reset(response.store);

        delete response.manufacturer;
        delete response.category;
        delete response.color;
        delete response.price;
        delete response.store;

        return response;
    },

    fetch: function(options) {
        options = options || {};
        options.data = options.data || {};
        _.extend(options.data, this.toJSON());

        return this.constructor.__super__.fetch.call(this, options);
    }
});
