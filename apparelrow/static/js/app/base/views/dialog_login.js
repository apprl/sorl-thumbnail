App.Views.DialogLogin = Backbone.View.extend({

    className: 'dialog-content group dialog-login',
    title: $('#dialog_login_template').data('title'),
    template: _.template($('#dialog_login_template').html()),

    events: {
        'click .btn-yes': 'yes',
        'click .btn-no': 'no',
        'click .btn-cancel': 'cancel'
    },

    initialize: function(options) {
        this.dispatcher = options.dispatcher;
    },

    no: function(e) {
        this.model._dirty = false;
        App.Events.trigger('popup_dispatcher:hide');

        login_function(function() {
            window.location.reload(false);
        });

        return false;
    },

    yes: function(e) {
        App.Events.trigger('popup_dispatcher:hide', true);
        this.dispatcher.show('dialog_save', true);

        return false;
    },

    cancel: function(e) {
        App.Events.trigger('popup_dispatcher:hide');

        return false;
    },

    render: function() {
        this.$el.html(this.template());

        return this;
    }

});
