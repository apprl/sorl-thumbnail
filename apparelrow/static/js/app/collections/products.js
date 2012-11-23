window.App.Collections.Products = Backbone.Collection.extend({

    model: App.Models.Product,
    url: '/products',

    parse: function(response) {
        return response.products;
    }

});
