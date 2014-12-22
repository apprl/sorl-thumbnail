App.Views.LookComponentCollage = App.Views.LookComponent.extend({

    className: 'product',

    template: _.template($('#look_component_collage').html()),

    active: false,

    initialize: function() {
        App.Events.on('lookedit:reposition', this.reposition, this);
        App.Events.on('lookedit:rescale', this.rescale, this);
        App.Events.on('lookedit:clicked', this.set_inactive, this);
        this.$container = $('.look-container');
    },

    info: function(e) {
        if(this.model.has('product') && !$(e.target).is('.delete') && !this.$el.is('.ui-draggable-dragging')) {
            // TODO: this.model.get('product') is not a real model
            App.Events.trigger('widget:product:info', new App.Models.Product(this.model.get('product')));

            return false;
        }
    },

    set_active: function(e) {
        this.$el.addClass('active');
        this.active = true;
        App.Events.trigger('look_edit:product:active', this);
        // TODO: cannot use backbone events because click event must bind after
        // draggable events
        if (this.hammertime) {
            this.enableTouchGestures();
        } else {
            this.$el.resizable("enable");
            this.$el.rotatable("enable");
        }
        e.stopPropagation();
    },

    set_inactive: function(e) {
        this.$el.removeClass('active');
        this.active = false;
        App.Events.trigger('look_edit:product:inactive', this);
        if (this.hammertime) {
             this.disableTouchGestures();
        } else {
            this.$el.resizable("disable");
            this.$el.rotatable("disable");
        }
    },

    rescale: function(scale) {
        var width = this.model.get('width'),
            height = this.model.get('height');
        this.$el.css({width: width*scale, height: height*scale});
        this.set_size(width*scale, height*scale);
        this.reposition({x:this.model.get('left')*(1-scale), y:this.model.get('top')*(1-scale)});
    },

    reposition: function(adjustments) {
        var new_left = this.model.get('left') - adjustments.x,
            new_top = this.model.get('top') - adjustments.y;

        this.set_position(new_left, new_top);
        this.$el.css({left: new_left, top: new_top});
    },

    set_size: function(width, height) {
        this.model.set({width: width, height: height}, {silent: true});
        App.Events.trigger('look:dirty');
    },

    set_position: function(left, top) {
        this.model.set({left: left, top: top}, {silent: true});
        App.Events.trigger('look:dirty');
    },

    enableTouchGestures: function() {
        this.hammertime.get('pinch').set({ enable: true });

        this.hammertime.on('pinch', _.bind(function (event) {
            var new_width = this.model.get('width') * event.scale;
            var new_height = this.model.get('height') * event.scale;
            if (new_width >= 50 && new_height >= 50) {
                this.$el.css({width: new_width, height: new_height});
            }
            this.rotate(event.rotation + this.model.get('rotation'));
        }, this));

        this.hammertime.on('pinchend', _.bind(function(event) {
            var new_width = this.model.get('width') * event.scale;
            var new_height = this.model.get('height') * event.scale;
            new_width = Math.min(new_width, this.$container.width() - this.$el.position().left);
            new_height = Math.min(new_height, this.$container.height() - this.$el.position().top);

            this.model.set({width: new_width, height: new_height, rotation: event.rotation}, {silent: true});
            App.Events.trigger('look:dirty');
        }, this));
    },

    disableTouchGestures: function() {
        this.hammertime.off('pinch pinchend');
        this.hammertime.get('pinch').set({ enable: false });
    },

    toggle_active: function(e) {
        if (!this.active) {
            this.set_active(e)
        } else {
            this.set_inactive(e);
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

    _min_zindex: function() {
        var current_min = 0;
        $('.look-container .product').each(function(index, element) {
            var current_value = parseInt($(element).css('z-index'), 10);
            if (current_value < current_min) {
                current_min = current_value;
            }
        });
        return current_min;
    },

    rotate: function(deg) {
        this.$el.css({
            'transform': 'rotate(' + deg +'deg)',
            '-moz-transform': 'rotate(' + deg + 'deg)',
            '-webkit-transform': 'rotate(' + deg + 'deg)',
            '-o-transform': 'rotate(' + deg + 'deg)',
            '-ms-transform': 'rotate(' + deg + 'deg)'
        });
    },

    render: function() {
        this.$el.css({'left': this.model.get('left'),
                      'top': this.model.get('top'),
                      'width': this.model.get('width'),
                      'height': this.model.get('height'),
                      'z-index': this.model.get('z_index'),
                      position: 'absolute'});

        this.rotate(this.model.get('rotation'));

        this.$el.toggleClass('flipped', this.model.get('flipped'));
        this.set_position(this.model.get('left'), this.model.get('top'));
        this.set_size(this.model.get('width'), this.model.get('height'));

        this.$el.html(this.template(this.model.toJSON()));

        this.$el.css('z-index', this._max_zindex() + 1);

         if (isMobileDevice()) {
            this.hammertime = new Hammer(this.$el[0]);
            this.hammertime.on('pan', _.bind(function(event) {
                var new_left = this.model.get('left') + event.deltaX,
                    new_top = this.model.get('top') + event.deltaY;

                this.$el.css({'left':new_left, 'top':new_top});
            }, this));
            this.hammertime.on('panend', _.bind(function(event) {
                new_left = Math.min(Math.max(0, new_left), this.$container.width() - this.$el.width());
                new_top = Math.min(Math.max(0, new_top), this.$container.height() - this.$el.height());
                this.$el.css({'left':new_left, 'top':new_top});
                this.set_position(new_left, new_top);
            },this));
        } else {

             this.$el.resizable({
                 containment: this.$container,
                 aspectRatio: true,
                 disabled: true,
                 maxHeight: this.$container.height(),
                 maxWidth: this.$container.width(),
                 minHeight: 50,
                 minWidth: 50,
                 handles: "se, ne, sw, nw",
                 create: _.bind(function (event, ui) {
                     var z_index = $(event.target).css('z-index');
                     if (!isNaN(parseInt(z_index))) {
                         this.model.set({z_index: z_index}, {silent: true});
                     }

                     $(event.target).find('.ui-resizable-handle').css('display', '');

                 }, this),
                 stop: _.bind(function (event, ui) {
                     this.set_size(ui.size.width, ui.size.height);
                 }, this)
             });

             this.$el.draggable({
                 stack: '.product',
                 cancel: '.ui-rotatable-handle',
                 containment: this.$container,
                 stop: _.bind(function (event, ui) {
                     var z_index = $(event.target).css('z-index');
                     if (!isNaN(parseInt(z_index))) {
                         this.model.set({z_index: z_index}, {silent: true});
                     }
                     this.set_position(ui.position.left, ui.position.top);
                 }, this)
             });

             this.$el.rotatable({
                 handles: 'n',
                 disabled: false,
                 rotate: _.bind(function (event, ui) {
                     this.rotate(ui.rotation);
                 }, this),
                 stop: _.bind(function (event, ui) {
                     this.model.set({rotation: ui.rotation}, {silent: true});
                     App.Events.trigger('look:dirty');
                 }, this)
             });
        }
        this.$el.on('mousedown click', _.bind(this.set_active, this));



        return this;
    }

});
