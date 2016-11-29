App.Views.DialogSaving = Backbone.View.extend({

    className: 'dialog-content group',
    title: $('#popup_saving').data('title'),
    template: _.template($('#popup_saving').html()),

    events: {
        'click .btn-ok': 'ok'
    },

    ok: function(e) {
        App.Events.trigger('popup_dispatcher:hide');

        return false;
    },

    render: function() {
        this.$el.html(this.template());

        return this;
    }

});
