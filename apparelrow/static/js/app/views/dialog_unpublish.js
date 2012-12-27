App.Views.DialogUnpublish = Backbone.View.extend({

    className: 'dialog-content group',
    title: gettext('Unpublish look?'),
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
        this.model.set('published', false);
        this.model.save();

        $('.button-container .btn-save').text(gettext('Save draft'));

        App.Events.trigger('popup_dispatcher:hide');
    },

    render: function() {
        this.$el.html(this.template());

        return this;
    }

});
