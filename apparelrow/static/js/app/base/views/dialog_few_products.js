App.Views.DialogFewProducts = Backbone.View.extend({

    className: 'dialog-content group',
    title: "",
    template: _.template($('#dialog_few_products').html()),

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
