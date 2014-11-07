App.Views.LookComponentPhoto = App.Views.LookComponent.extend({

    className: 'hotspot',

    template: _.template($('#look_component_photo').html()),

    info: function(e) {
        if(this.model.has('product') && !$(e.target).is('.delete') && !this.$el.is('.ui-draggable-dragging')) {
            // TODO: this.model.get('product') is not a real model
            App.Events.trigger('widget:product:info', new App.Models.Product(this.model.get('product')));

            return false;
        }
    },

    render: function() {
        this.$el.css({left: this.model.get('left'),
                      top: this.model.get('top'),
                      width: this.model.get('width'),
                      height: this.model.get('height'),
                      'z-index': this.model.get('z_index'),
                      position: 'absolute'});

        this.$el.html(this.template(this.model.toJSON()));

        this.$el.draggable({
            stack: '.hotspot',
            containment: $('.look-container'),
            stop: _.bind(function(event, ui) {
                this.model.set({left: ui.position.left, top: ui.position.top}, {silent: true});
                App.Events.trigger('look:dirty');
            }, this)
        });

        // TODO: cannot use backbone events because click event must bind after
        // draggable events
        this.$el.on('click', _.bind(this.info, this));

        return this;
    }

});
