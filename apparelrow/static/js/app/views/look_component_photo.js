App.Views.LookComponentPhoto = Backbone.View.extend({

    template: _.template($('#look_component_photo').html()),

    events: {
        'click .delete': 'delete_component',
    },

    initialize: function() {
        this.model.on('change', this.render, this);
    },

    delete_component: function(e) {
        this.remove();
        this.model.destroy();

        e.preventDefault();
    },

    render: function() {
        console.log('render component', this.model);
        this.$el.html(this.template(this.model.toJSON()));
        this.delegateEvents();

        return this;
    }

});
