App.Views.LookEditToolbar = Backbone.View.extend({

    el: '.lookedit_toolbar',

    events: {
    },

    active_component: false,

    initialize: function () {
        App.Events.on('look_edit:product:active', this.activate_edit, this);
        App.Events.on('look_edit:product:inactive', this.deactivate_edit, this);
    },

    activate_edit: function(component) {
        if (this.active_component != component) {
            if (this.active_component) this.active_component.set_inactive();
            this.active_component = component;
            this.$el.addClass('active');
        }
    },

    deactivate_edit: function(component) {
        this.active_component = false;
        this.$el.removeClass('active');
    }
});