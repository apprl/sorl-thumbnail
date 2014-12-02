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
        var gender = this.get('gender');
        var user_id = this.get('user_id');
        this.clear({silent: true});
        this.set(_.extend(this.defaults, {gender: gender, user_id: user_id}));
    },

    facet: function(data) {
        if(!data.value || data.value == 0 || data.value == '') {
            this.unset(data.type);
        } else {
            this.set(data.type, data.value);
        }
    }

});
