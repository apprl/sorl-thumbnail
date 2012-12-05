App.Views.LookEditPopup = Backbone.View.extend({

    initialize: function() {
        this.active = false;

        App.Events.on('look_edit:product:info', this.show, this);
    },

    show: function(model) {
        console.log('render a popup and show it for product with id', model.id);

        this.render();
    },

    hide: function() {

    },

    render: function() {

    }

});
