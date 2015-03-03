window.App.Collections.Products = Backbone.Collection.extend({

    model: App.Models.Product,
    url: '/products',

    initialize: function() {
        this.next_page = false;
    },

    parse: function(response) {
        if(response.hasOwnProperty('next_page')) {
            this.next_page = response.next_page;
        } else {
            this.next_page = false;
        }

        return response.products;
    },

    fetch_next: function(success_callback) {
        if(this.next_page) {
            this.fetch({url: this.next_page, success: success_callback});
        }
    }

});
