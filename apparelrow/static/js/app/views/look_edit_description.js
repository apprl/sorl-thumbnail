App.Views.LookEditDescription = Backbone.View.extend({

    el: '.column_one',

    events: {
        'click': 'edit',
        'blur input': 'on_blur',
        'keypress input': 'on_keypress'
    },

    initialize: function() {
        this.model.on('change:title', this.render, this);

        this.render();
    },

    edit: function() {
        this.$el.find('h1').hide();
        this.$el.find('input').show().focus();
    },

    on_blur: function() {
        this.save();
    },

    on_keypress: function(e) {
        if (e.keyCode != 13) return;

        this.save();
    },

    save: function() {
        this.model.set('title', this.$el.find('input').val());
    },

    render: function() {
        var title = this.model.get('title');
        if(!title) {
            title = 'Your look name here';
        }
        this.$el.find('h1').html(title).show();
        this.$el.find('input').val(title).hide();

        return this;
    }

});
