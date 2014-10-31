App.Views.Header = Backbone.View.extend({
    el: '.body-header',
    template: _.template($('.body-header').html()),

    events: {
        'click .btn-delete': 'header_delete',
        'click .btn-reset': 'header_reset',
        'click .btn-save': 'header_save',
        'click .btn-unpublish': 'header_unpublish',
        'click .btn-publish': 'header_publish'
    },

    initialize: function(options) {
        this.popup_dispatcher = new App.Views.PopupDispatcher();
        this.popup_dispatcher.add('dialog_reset', new App.Views.DialogReset());
        this.popup_dispatcher.add('dialog_delete', new App.Views.DialogDelete());
        this.popup_dispatcher.add('dialog_save', new App.Views.DialogSave({model: options.model, title: $('#dialog_save_template').data('title')}));
        this.popup_dispatcher.add('dialog_publish', new App.Views.DialogSave({model: options.model, title: $('#dialog_publish_template').data('title')}));
        this.popup_dispatcher.add('dialog_unpublish', new App.Views.DialogUnpublish());
    },

    header_reset: function() {
        this.popup_dispatcher.show('dialog_reset');

        return false;
    },

    header_delete: function() {
        this.popup_dispatcher.show('dialog_delete');

        return false;
    },

    header_publish: function() {
        this.popup_dispatcher.show('dialog_publish');

        return false;
    },

    header_unpublish: function() {
        this.popup_dispatcher.show('dialog_unpublish');

        return false;
    },

    header_save: function() {
        this.popup_dispatcher.show('dialog_save');

        return false;
    }
});