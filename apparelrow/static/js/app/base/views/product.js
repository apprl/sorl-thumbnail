App.Views.Product = Backbone.View.extend({

    tagName: 'li',
    template: _.template($('#product_small_template').html()),

    events: {
        'mouseenter .image-small, .hover': 'mouseenter',
        'mouseleave .image-small, .hover': 'mouseleave',
        'click .btn-product-info': 'info',
        'click .btn-add': 'add',
        'click .product-small': 'mouseenter'
    },

    mouseenter: function(e) {
        this.$el.find('.hover').show();
    },

    mouseleave: function(e) {
        this.$el.find('.hover').hide();
    },

    info: function(e) {
        App.Events.trigger('look_edit:product:info', this.model);

        return false;
    },

    add: function(e) {
        App.Events.trigger('look_edit:product:add', this.model);

        return false;
    },

    render: function() {
        this.$el.html(this.template(this.model.toJSON()));

        return this;
    }

});
