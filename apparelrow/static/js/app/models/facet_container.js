window.App.Models.FacetContainer = window.App.Models.WidgetModelBase.extend({
    url: '/products',

    defaults: {
        'facet': 'manufacturer,category,color,price'
    },

    initialize: function() {
        this.manufacturer = new App.Collections.Facets(),
        this.color = new App.Collections.Facets(),
        this.category = new App.Collections.Facets(),
        this.price = new App.Collections.Facets()
    },

    parse: function(response) {
        this.manufacturer.reset(response.manufacturer);
        this.category.reset(response.category);
        this.color.reset(response.color);
        this.price.reset(response.price);

        delete response.manufacturer;
        delete response.category;
        delete response.color;
        delete response.price;

        return response;
    },

    fetch: function(options) {
        options = options || {};
        options.data = options.data || {};
        _.extend(options.data, this.toJSON());

        return this.constructor.__super__.fetch.call(this, options);
    }
});
