App.Views.Product = Backbone.View.extend({

    tagName: 'li',

    render: function() {
        return this.$el = $(this.model.get('template'));
    }

});
