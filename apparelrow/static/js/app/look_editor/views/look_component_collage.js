App.Views.LookComponentCollage = App.Views.LookComponent.extend({

    className: 'product',

    template: _.template($('#look_component_collage').html()),

    info: function(e) {
        if(this.model.has('product') && !$(e.target).is('.delete') && !this.$el.is('.ui-draggable-dragging')) {
            // TODO: this.model.get('product') is not a real model
            App.Events.trigger('widget:product:info', new App.Models.Product(this.model.get('product')));

            return false;
        }
    },

    _max_zindex: function() {
        var current_max = 0;
        $('.look-container .product').each(function(index, element) {
            var current_value = parseInt($(element).css('z-index'), 10);
            if(current_value > current_max) {
                current_max = current_value;
            }
        });
        return current_max;
    },

    render: function() {
        this.$el.css({left: this.model.get('left'),
                      top: this.model.get('top'),
                      width: this.model.get('width'),
                      height: this.model.get('height'),
                      'z-index': this.model.get('z_index'),
                      'transform': 'rotate(' + this.model.get('rotation') + 'deg)',
                      '-moz-transform': 'rotate(' + this.model.get('rotation') + 'deg)',
                      '-webkit-transform': 'rotate(' + this.model.get('rotation') + 'deg)',
                      '-o-transform': 'rotate(' + this.model.get('rotation') + 'deg)',
                      '-ms-transform': 'rotate(' + this.model.get('rotation') + 'deg)',
                      position: 'absolute'});

        this.$el.html(this.template(this.model.toJSON()));

        var container = $('#collage');

        this.$el.css('z-index', this._max_zindex() + 1);

        this.$el.resizable({
            containment: container,
            aspectRatio: true,
            autoHide: true,
            maxHeight: container.height(),
            maxWidth: container.width(),
            minHeight: 50,
            minWidth: 50,
            create: _.bind(function(event, ui) {
                var z_index = $(event.target).css('z-index');
                if(!isNaN(parseInt(z_index))) {
                    this.model.set({z_index: z_index}, {silent: true});
                }
            }, this),
            stop: _.bind(function(event, ui) {
                this.model.set({width: ui.size.width, height: ui.size.height}, {silent: true});
                App.Events.trigger('look:dirty');
            }, this)
        });

        this.$el.draggable({
            stack: '.product',
            cancel: '.ui-rotatable-handle',
            containment: $('.look-container'),
            stop: _.bind(function(event, ui) {
                var z_index = $(event.target).css('z-index');
                if(!isNaN(parseInt(z_index))) {
                    this.model.set({z_index: z_index}, {silent: true});
                }
                this.model.set({left: ui.position.left, top: ui.position.top}, {silent: true});
                App.Events.trigger('look:dirty');
            }, this)
        });

        this.$el.rotatable({
            handles: 'nw',
            autoHide: true,
            stop: _.bind(function(event, ui) {
                this.model.set({rotation: ui.rotation}, {silent: true});
                App.Events.trigger('look:dirty');
            }, this)
        });

        // TODO: cannot use backbone events because click event must bind after
        // draggable events
        this.$el.on('click', _.bind(this.info, this));

        return this;
    }

});
