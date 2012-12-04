App.Views.LookEditDescription = Backbone.View.extend({

    el: '.look-description',

    events: {
        'blur textarea': 'on_blur',
        'keypress textarea': 'on_keypress'
    },

    initialize: function() {
        this.model.on('change:description', this.render, this);
    },

    on_blur: function() {
        this.save();
    },

    on_keypress: function(e) {
        if (e.keyCode != 13) return;

        this.save();
    },

    save: function() {
        this.model._dirty = true;
        this.model.set('description', this.$el.find('textarea').val());
        this.render();
    },

    render: function() {
        this.$el.find('textarea').val(this.model.get('description'));

        return this;
    }

});
