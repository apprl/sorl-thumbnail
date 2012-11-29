App.Views.Product = Backbone.View.extend({

    tagName: 'li',
    template: _.template($('#product_small_template').html()),

    events: {
        'mouseenter img': 'mouseenter',
        'mouseleave img': 'mouseleave'
    },

    mouseenter: function() {
        console.log('hover');
    },

    mouseleave: function() {
        console.log('leave');
    },

    render: function() {
        this.$el.append(this.template(this.model.toJSON()));

        return this;
    }

});
