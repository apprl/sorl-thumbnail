App.Views.DialogReset = Backbone.View.extend({

    className: 'dialog-content group',
    title: $('#dialog_reset_template').data('title'),
    template: _.template($('#dialog_reset_template').html()),

    events: {
        'click .btn-yes': 'yes',
        'click .btn-no': 'no'
    },

    no: function(e) {
        App.Events.trigger('popup_dispatcher:hide');

        return false;
    },

    yes: function(e) {
        App.Events.trigger('widget:reset');
        App.Events.trigger('popup_dispatcher:hide');

        return false;
    },

    render: function() {
        this.$el.html(this.template());

        return this;
    }

});
