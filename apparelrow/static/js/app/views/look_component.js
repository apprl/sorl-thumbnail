App.Views.LookComponent = Backbone.View.extend({

    events: {
        'click .delete': 'on_delete',
        'click': 'on_click'
    },

    initialize: function() {
        this.model.on('change', this.render, this);
    },

    on_delete: function(e) {
        this.remove();
        this.collection.remove(this.model);

        e.preventDefault();
    },

    on_click: function(e) {
        if(this.model.has('product')) {
            App.Events.trigger('look_edit:product:info', this.model.get('product'));
        }
    },

    render: function() {
        this.$el.html(this.template(this.model.toJSON()));
        this.delegateEvents();

        return this;
    }

});
