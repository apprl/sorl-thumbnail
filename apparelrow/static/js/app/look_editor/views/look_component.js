App.Views.LookComponent = Backbone.View.extend({

    events: {
        'click .delete': 'on_delete'
       /* 'mouseenter': 'on_enter',
        'mouseleave': 'on_leave'*/
    },

    initialize: function() {
        this.model.on('change', this.render, this);
    },

    on_delete: function(e) {
        this.remove();
        this.collection.remove(this.model);

        e.preventDefault();
    },

    on_enter: function(e) {
        if(external_look_type == 'collage') {
            this.$el.find('.delete').show();
        }
    },

    on_leave: function(e) {
        if(external_look_type == 'collage') {
            this.$el.find('.delete').hide();
        }
    },

    render: function() {
        this.$el.html(this.template(this.model.toJSON()));
        this.delegateEvents();

        return this;
    }

});
