App.Views.DialogDelete = Backbone.View.extend({

    className: 'dialog-content group',
    title: $('#dialog_delete_template').data('title'),
    template: _.template($('#dialog_delete_template').html()),

    events: {
        'click .btn-yes': 'yes',
        'click .btn-no': 'no'
    },

    no: function(e) {
        App.Events.trigger('popup_dispatcher:hide');

        return false;
    },

    yes: function(e) {
        this.model._dirty = false;
        this.model.destroy({success: function() {
            window.location.replace('/looks/');
        }});
    },

    render: function() {
        this.$el.html(this.template());

        return this;
    }

});
