App.Views.FilterProductPrice = Backbone.View.extend({

    tagName: 'div',
    className: 'price-filter',

    events: {
        'change': 'update',
    },

    initialize: function(options) {
        this.collection.on('reset', this.render, this);
        this.render();
    },

    render: function() {
        var price_model = this.collection.at(0);
        if(price_model) {
            this.$el.text(price_model.get('min') + ', ' + price_model.get('max'));
        }

        return this;
    },

    update: function() {
        App.Events.trigger('facet_event', {type: 'price', value: '0,100000'});
    }

});
