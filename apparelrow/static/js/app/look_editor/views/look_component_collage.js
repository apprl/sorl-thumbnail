App.Views.LookComponentCollage = App.Views.LookComponent.extend({

    className: 'product',

    template: _.template($('#look_component_collage').html()),

    active: false,

    initialize: function() {
        App.Events.on('lookedit:update_measures', this.rescale, this);
        //App.Views.LookComponent.__super__.initialize(this);
        this.$container = $('.look-container');
    },

    info: function(e) {
        if(this.model.has('product') && !$(e.target).is('.delete') && !this.$el.is('.ui-draggable-dragging')) {
            // TODO: this.model.get('product') is not a real model
            App.Events.trigger('look_edit:product:info', new App.Models.Product(this.model.get('product')));

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
            this.$el.find('.delete').show();
        }
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
            this.$el.find('.delete').hide();
        }
    },

    rescale: function(measures) {
        var new_width = this.model.get('width_rel') * measures.width,
            ratio = this.model.get('height')/this.model.get('width'),
            new_height = ratio*new_width,
            new_left = this.model.get('left_rel') * measures.width,
            new_top = this.model.get('top_rel') * measures.height;

        this.$el.css({
            left: new_left,
            top:  new_top,
            width: new_width,
            height: ratio*new_width
        });

        this.set_position(new_left, new_top, true);
        this.set_size(new_width, new_height, true);
    },

    set_size: function(width, height, rescaled) {
        this.model.set({width: width, height: height}, {silent: true});
        if (!rescaled) {

            this.model.set('width_rel', width/this.$container.width());
        }
        App.Events.trigger('look:dirty');
    },

    set_position: function(left, top, rescaled) {
        this.model.set({left: left, top: top}, {silent: true});
        if (!rescaled) {
            this.model.set({left_rel: left/this.$container.width(), top_rel: top/this.height()});
        }
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
            this.$el.css({'transform': 'rotate(' + event.rotation + 'deg)'});
            if (event.isFinal) {
                new_width = Math.min(new_width, this.$container.width() - this.$el.position().left);
                new_height = Math.min(new_height, this.$container.height() - this.$el.position().top);

                this.$el.css({width: new_width, height: new_height});
                this.model.set_size(new_width, new_height);
                this.model.set({rotation: event.rotation}, {silent: true});
            }
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

    render: function() {
        this.$el.css({'z-index': this.model.get('z_index'),
                      'transform': 'rotate(' + this.model.get('rotation') + 'deg)',
                      '-moz-transform': 'rotate(' + this.model.get('rotation') + 'deg)',
                      '-webkit-transform': 'rotate(' + this.model.get('rotation') + 'deg)',
                      '-o-transform': 'rotate(' + this.model.get('rotation') + 'deg)',
                      '-ms-transform': 'rotate(' + this.model.get('rotation') + 'deg)',
                      position: 'absolute'});


        this.set_position(this.model.get('left'), this.model.get('top'), true);
        this.set_size(this.model.get('width'), this.model.get('height'), true);

        this.$el.html(this.template(this.model.toJSON()));

        this.$el.css('z-index', this._max_zindex() + 1);

         if (isMobileDevice()) {
            this.hammertime = new Hammer(this.$el[0]);
            this.hammertime.on('pan', _.bind(function(event) {
                var new_left = this.model.get('left') + event.deltaX,
                    new_top = this.model.get('top') + event.deltaY;

                this.$el.css({'left':new_left, 'top':new_top});
                if (event.isFinal) {
                    new_left = Math.min(Math.max(0, new_left), this.$container.width() - this.$el.width());
                    new_top = Math.min(Math.max(0, new_top), this.$container.height() - this.$el.height());
                    this.$el.css({'left':new_left, 'top':new_top});
                    this.set_position(new_left, new_top);
                }

            }, this));
        } else {

             this.$el.resizable({
                 containment: this.$container,
                 aspectRatio: true,
                 disabled: true,
                 maxHeight: this.$conatainer.height(),
                 maxWidth: this.$container.width(),
                 minHeight: 50,
                 minWidth: 50,
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
                 handles: 'nw',
                 disabled: true,
                 stop: _.bind(function (event, ui) {
                     this.model.set({rotation: ui.rotation}, {silent: true});
                     App.Events.trigger('look:dirty');
                 }, this)
             });
        }
        this.$el.on('click', _.bind(this.toggle_active, this));



        return this;
    }

});
