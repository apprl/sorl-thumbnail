App.Views.LookComponent = Backbone.View.extend({

    events: {
        'click .delete': 'on_delete'
    },

    initialize: function() {
        this.model.on('change', this.render, this);
    },

    on_delete: function(e) {
        this.remove();
        this.collection.remove(this.model);
        if (e) {
            e.preventDefault();
        }
    },

    render: function() {
        this.$el.html(this.template(this.model.toJSON()));
        this.delegateEvents();

        return this;
    }

});
