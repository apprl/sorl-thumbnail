App.Views.LookComponentCollage = App.Views.LookComponent.extend({

    className: 'product',

    template: _.template($('#look_component_collage').html()),

    active: false,

    events: {
        'mouseover': 'togglehover',
        'mouseout' : 'togglehover'
    },

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

    togglehover: function() {
        this.$el.toggleClass('hover');
    },

    set_active: function(e) {
        this.$el.addClass('active');
        this.active = true;
        App.Events.trigger('look_edit:product:active', this);
        // TODO: cannot use backbone events because click event must bind after
        // draggable events
        if (this.hammertime) {
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
        } else {
            this.$el.resizable("disable");
            this.$el.rotatable("disable");
        }
    },

    rescale: function(scale) {
        var new_width = Math.round(this.model.get('width')*scale),
            new_height = Math.round(this.model.get('height')*scale);
        this.$el.css({width: width*scale, height: height*scale});
        this.set_size(width*scale, height*scale);
        this.reposition({x:this.model.get('left')*(1-scale), y:this.model.get('top')*(1-scale)});
    },

    reposition: function(adjustments) {
        var new_left = this.model.get('left') - adjustments.x,
            new_top = this.model.get('top') - adjustments.y;

        this.set_position(new_left, new_top);
    },

    set_size: function(width, height) {
        this.model.set({width: width, height: height}, {silent: true});
        App.Events.trigger('look:dirty');
    },

    set_position: function(left, top) {
        this.model.set({left: left, top: top}, {silent: true});
        this.$el.css({'left': left, 'top': top});
        App.Events.trigger('look:dirty');
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

    applyTransform: function() {
        var value = [
            'translate3d(' + this.transform.translate.x + 'px, ' + this.transform.translate.y + 'px, 0)',
            'scale(' + this.transform.scale + ', ' + this.transform.scale + ')',
            'rotate('+ this.transform.angle + 'deg)'
        ];

        value = value.join(" ");
        this.$el.css({'-webkit-transform': value, '-moz-transform': value, 'transform': value});
    },

    getRecoup: function(position) {
        var left = parseInt(this.model.get('left'),10);
        left = isNaN(left) ? 0 : left;
        var top = parseInt(this.model.get('top'),10);
        top = isNaN(top) ? 0 : top;
        return {'left': left - position.left, 'top': top - position.top};
    },

    render: function() {
        this.$el.css({'left': this.model.get('left'),
                      'top': this.model.get('top'),
                      'width': this.model.get('width'),
                      'height': this.model.get('height'),
                      'z-index': this.model.get('z_index'),
                      position: 'absolute'});



        this.$el.toggleClass('flipped', this.model.get('flipped'));

        this.set_position(this.model.get('left'), this.model.get('top'));

        this.set_size(this.model.get('width'), this.model.get('height'));

        this.$el.html(this.template(this.model.toJSON()));

        this.$el.css('z-index', this._max_zindex() + 1);

        this.transform = {
            'translate': {'x':0, 'y':0},
            'angle': this.model.get('rotation') ? this.model.get('rotation') : 0,
            'scale': 1
        };
        this.applyTransform();

        if (isMobileDevice()) {
            this.hammertime = new Hammer.Manager(this.$el.children('img')[0]);

            this.hammertime.add(new Hammer.Pan({ threshold: 0, pointers: 0 }));

            this.hammertime.add(new Hammer.Pinch({ threshold: 0 })).recognizeWith(this.hammertime.get('pan'));
            this.hammertime.add(new Hammer.Rotate({ threshold: 0 })).recognizeWith([this.hammertime.get('pan'), this.hammertime.get('pinch')]);

            this.hammertime.on("panstart panmove", _.bind(function(event) {
                this.transform.translate = {'x': event.deltaX, 'y': event.deltaY};
                this.applyTransform();
            }, this));
            this.hammertime.on("panend",_.bind(function(event) {
                this.set_position(this.$el.position().left + (this.recoup ? this.recoup.left : 0), this.$el.position().top + (this.recoup ? this.recoup.top : 0));
                this.transform.translate = {'x': 0, 'y': 0};
                this.applyTransform();
            }, this));
            this.hammertime.on("rotatestart rotatemove", _.bind(function(event) {
                this.recoup = false;
                this.transform.angle = event.rotation;
                this.applyTransform();
            }, this));
            this.hammertime.on("rotateend", _.bind(function(event) {
                this.transform.angle = event.rotation;
                this.model.set('rotation', event.rotation);
                this.applyTransform();
                this.recoup = this.getRecoup(this.$el.position());
                this.$el.css({'left': this.recoup.left + this.model.get('left'), 'top': this.recoup.top + this.model.get('top')});
            }, this));
            this.hammertime.on("pinchstart pinchmove", _.bind(function (event) {
                this.transform.scale = event.scale;
                this.applyTransform();
            }, this));
            this.hammertime.on("pinchend", _.bind(function(event) {
                var new_width = Math.round(this.model.get('width') * this.transform.scale);
                var new_height = Math.round(this.model.get('height') * this.transform.scale);
                this.set_size(new_width, new_height);
                this.$el.css({'width': new_width, 'height': new_height});
                this.transform.scale = 1;
                this.applyTransform();
            }, this));
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
                 start: _.bind(function(event, ui) {
                 }, this),
                 stop: _.bind(function (event, ui) {
                     this.set_size(ui.size.width, ui.size.height);
                     this.set_position(ui.position.left, ui.position.top);
                 }, this)
             });

             this.$el.draggable({
                 stack: '.product',
                 cancel: '.ui-rotatable-handle',
                 containment: this.$container,
                 start: _.bind(function (event, ui) {
                     var recoup = this.getRecoup(ui.position);
                     recoupLeft = recoup['left'];
                     recoupTop = recoup['top'];
                 }, this),
                 drag: function (event, ui) {
                    ui.position.left += recoupLeft;
                    ui.position.top += recoupTop;
                 },
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
                     this.transform.angle = ui.rotation;
                     this.applyTransform();
                 }, this),
                 stop: _.bind(function (event, ui) {
                     this.model.set({rotation: ui.rotation}, {silent: true});
                     App.Events.trigger('look:dirty');
                 }, this)
             });
        }
        this.$el.on('mousedown click touchstart', _.bind(this.set_active, this));



        return this;
    }

});
