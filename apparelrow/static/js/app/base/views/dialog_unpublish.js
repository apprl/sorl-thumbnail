App.Views.DialogUnpublish = Backbone.View.extend({

    className: 'dialog-content group',
    title: $('#dialog_unpublish_template').data('title'),
    template: _.template($('#dialog_unpublish_template').html()),

    events: {
        'click .btn-yes': 'yes',
        'click .btn-no': 'no'
    },

    no: function(e) {
        App.Events.trigger('popup_dispatcher:hide');
        return false;
    },

    yes: function(e) {
        $('.button-container .btn-save').text($('.button-container .btn-save').data('save-draft-text'));
        App.Events.trigger('popup_dispatcher:hide');
    },

    render: function() {
        this.$el.html(this.template());

        return this;
    }

});
