App.Views.LookEditToolbar = Backbone.View.extend({

    el: '.lookedit_toolbar',

    events: {
        'click .component_clone': 'clone_component',
        'click .component_forward': 'forward_component',
        'click .component_back': 'back_component',
        'click .component_flip': 'flip_component',
        'click .component_delete': 'delete_component',
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

    deactivate_edit: function() {
        this.active_component = false;
        this.$el.removeClass('active');
    },

    clone_component: function() {
        if (this.active_component) {
            var new_component = this.active_component.model.clone();
            new_component.unset('id');
            new_component.set('cid', 'c' + _.random(1000, 2000));
            $container = $('.look-container');
            new_component.set({z_index: this.active_component._max_zindex()+1, left: $container.width()/2 - new_component.get('width')/2, top: $container.height()/2 - new_component.get('height')/2});
            window.look_edit.model.components.add(new_component);
        }
    },

    forward_component: function() {
        if (this.active_component) {
            var z_index = this.active_component._max_zindex() + 1;
            this.active_component.$el.css('z-index', z_index);
            this.active_component.model.set({z_index: z_index}, {silent: true});
        }
    },

    back_component: function() {
        if (this.active_component) {
            var z_index = this.active_component._min_zindex() -1;
            this.active_component.$el.css('z-index', Math.max(0,z_index));
            this.active_component.model.set({z_index: z_index}, {silent: true});
        }
    },

    flip_component: function() {
        if (this.active_component) {
            var flipped = this.active_component.$el.hasClass('flipped');
            this.active_component.$el.toggleClass('flipped');
            this.active_component.model.set({flipped: !flipped}, {silend: true});
        }
    },

    delete_component: function() {
        if (this.active_component) {
            this.active_component.on_delete();
            this.deactivate_edit(false);
        }
    }
});