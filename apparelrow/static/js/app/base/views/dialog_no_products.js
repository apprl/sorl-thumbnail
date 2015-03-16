App.Views.DialogNoProducts = Backbone.View.extend({

    className: 'dialog-content group',
    title: $('#dialog_no_products').data('title'),
    template: _.template($('#dialog_no_products').html()),

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
