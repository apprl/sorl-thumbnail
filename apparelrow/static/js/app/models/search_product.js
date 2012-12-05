window.App.Models.SearchProduct = Backbone.Model.extend({

    defaults: {
        gender: selected_gender,
        limit: 20
    },

    initialize: function() {
        App.Events.on('product:facet', this.on_facet, this);
    },

    // TODO: handle multiple selection of values
    on_facet: function(data) {
        if(!data.value || data.value == 0 || data.value == '') {
            this.unset(data.type);
        } else {
            this.set(data.type, data.value);
        }
    }

});
