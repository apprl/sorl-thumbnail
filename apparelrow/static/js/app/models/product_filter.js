window.App.Models.ProductFilter = Backbone.Model.extend({

    defaults: {
        gender: selected_gender,
        limit: 20
    },

    initialize: function() {
        App.Events.on('product:facet', this.facet, this);
        App.Events.on('product:reset', this.reset, this);
    },

    reset: function() {
        this.clear({silent: true});
        this.set(this.defaults);
    },

    facet: function(data) {
        if(!data.value || data.value == 0 || data.value == '') {
            this.unset(data.type);
        } else {
            this.set(data.type, data.value);
        }
    }

});
