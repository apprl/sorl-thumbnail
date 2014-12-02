App.Views.LookComponentPhoto = App.Views.LookComponent.extend({

    className: 'hotspot',

    template: _.template($('#look_component_photo').html()),

    initialize: function() {
        App.Events.on('lookedit:rescale', this.rescale, this);
        App.Views.LookComponent.__super__.initialize(this);
    },

    info: function(e) {
        if(this.model.has('product') && !$(e.target).is('.delete') && !this.$el.is('.ui-draggable-dragging')) {
            // TODO: this.model.get('product') is not a real model
            App.Events.trigger('look_edit:product:info', new App.Models.Product(this.model.get('product')));

            return false;
        }
    },

    rescale: function(measures) {
        var new_left = this.model.get('rel_left') * measures.width - this.model.get('width')/2,
            new_top = this.model.get('rel_top') * measures.height - this.model.get('height')/2;
        this.$el.css({
            left: new_left,
            top:  new_top
        });

        this.set_position(new_left, new_top, true);
    },

    set_position: function(left, top, rescaled) {
        this.model.set({left: left, top: top}, {silent: true});
        if (!rescaled) {
            var $container = $('.look-container');
            this.model.set({left_rel: (left+this.model.get('width')/2)/$container.width(), top_rel: (top+this.model.get('height')/2)/$container.height()});
        }
        App.Events.trigger('look:dirty');
    },

    render: function() {
        this.$el.css({left: this.model.get('left'),
                      top: this.model.get('top'),
                      width: this.model.get('width'),
                      height: this.model.get('height'),
                      'z-index': this.model.get('z_index'),
                      position: 'absolute'});

        this.set_position(this.model.get('left'), this.model.get('top'), true);

        this.$el.html(this.template(this.model.toJSON()));


        if (isMobileDevice()) {
            this.hammertime = new Hammer(this.$el[0]);
            this.hammertime.on('pan', _.bind(function(event) {
                this.$el.css('left', this.model.get('left') + event.deltaX);
                this.$el.css('top', this.model.get('top') + event.deltaY);
            }, this));
            this.hammertime.on('panend', _.bind(function(event) {
                this.model.set({left: this.$el.position().left, top: this.$el.position().top}, {silent: true});
            }, this));
        } else {
            this.$el.draggable({
                 stack: '.hotspot',
                 containment: $('.look-container'),
                 stop: _.bind(function (event, ui) {
                     this.set_position(ui.position.left, ui.position.top);
                 }, this)
            });
         }

        // TODO: cannot use backbone events because click event must bind after
        // draggable events
        this.$el.on('click', _.bind(this.info, this));

        return this;
    }

});
