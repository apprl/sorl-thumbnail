App.Views.LookEdit = App.Views.WidgetBase.extend({

    el: '#edit-look',
    template: _.template($('#edit_look_template').html()),

    events: {
        'click .look-container': 'on_click',
        'touch .look-container': 'on_click',
        'mousedown .look-container': 'inactivate'
    },

    initialize: function() {
        // Look component classes lookup
        this.component_view_classes = {
            'photo': App.Views.LookComponentPhoto,
            'collage': App.Views.LookComponentCollage
        };

        // Popup dispatcher
        this.popup_dispatcher = new App.Views.PopupDispatcher();
        this.popup_dispatcher.add('dialog_login', new App.Views.DialogLogin({model: this.model, dispatcher: this.popup_dispatcher}));

        // Look editor popup
        this.look_edit_popup = new App.Views.LookEditPopup({parent_view: this});

        this.initialize_temporary_image();

        // Model events and fetch model
        //this.model.on('change', this.render, this);
        this.model.on('change:image', this.render_image, this);
        this.model.on('destroy', this.render, this);

        this.model.components.on('add', this.add_component, this);
        this.model.components.on('remove', this.remove_component, this);
        this.model.components.on('reset', this.add_components, this);

        // TODO: is it ok to render on error? wil it work for look edits?
        this.model.fetch({error: _.bind(function() { this.render(); }, this), success: _.bind(function() { this.render(); }, this)});

        // Facebook button login
        if(!isAuthenticated) {
            // TODO: must turn off default click handler, better way to handle this?
            $('#nav-user .btn-facebook').off('click');
            $('.facebook-btn').attr('onclick', '').on('click', _.bind(this.login_popup, this));
        }

        this.model.on('change:published', function(model, value, options) {
            if(value === false) {
                var $button = $('.btn-unpublish');
                $button.text($button.data('publish-text')).addClass('btn-publish').removeClass('btn-unpublish');
            }
        }, this);

        // Create toolbar
        this.toolbar = new App.Views.LookEditToolbar();

        // Listen on product add
        App.Events.on('widget:product:add', this.pending_add_component, this);
        this.pending_product = false;
        this.pending_component = false;

        // Listen on widget events
        App.Events.on('widget:delete', this.delete_look, this);
        App.Events.on('widget:reset', this.render, this);
        App.Events.on('widget:save', this.save_look, this);
        App.Events.on('widget:publish', this.publish_look, this);
        App.Events.on('widget:unpublish', this.unpublish_look, this);


        $(window).on('resize onorientationchange', _.bind(this.update_sizes, this));
        App.Views.LookEdit.__super__.initialize(this);
        $(window).trigger('resize');
        if (external_look_type == 'collage') {
            this.disable_footer();
        }
    },

    login_popup: function() {
        this.popup_dispatcher.show('dialog_login');

        return false;
    },

    add_component: function(model, collection) {
        var view_class = this.component_view_classes[external_look_type];
        var view = new view_class({model: model, collection: collection});
        this.$('.look-container').append(view.render().el);
        // make sure startsplash is hidden
        $('#startsplash').hide();
    },

    add_components: function(collection) {
        collection.each(_.bind(function(model) { this.add_component(model, collection); }, this));
    },

    remove_component: function(model, collection) {
        // Reset pending component
        this.pending_component = false;

        this.model._dirty = true;
    },

    add_product_to_component: function(component, product) {
        component.set('product', product.toJSON());

        this.model._dirty = true;
    },

    pending_add_component: function(product) {
        // XXX: this code might be used in the future when we want to allow a
        // click in a photo without a pending product
        //if(this.pending_component && this.model.has('image')) {
            //this.add_product_to_component(this.model.components.getByCid(this.pending_component), product);
            //this.pending_component = false;
        //} else {

        if(external_look_type == 'collage') {
            this._create_collage_component(product);
        } else {
            this.pending_product = product;
            if (this.pending_event) {
                window.setTimeout(_.bind(function() {
                    this.on_click(this.pending_event);
                }, this), 500);
            }
        }
    },

    _get_hotspot: function(e) {
        // TODO: maybe use dynamic scale for hotspot size instead of 80x80
        var size = 80,
            $container = this.$el.find('.look-container'),
            container_offset = $container.offset(),
            container_width = $container.width() - size,
            container_height = $container.height() - size;
        return {top: Math.min(container_height, Math.max(0, e.pageY - container_offset.top - (size / 2))),
                left: Math.min(container_width, Math.max(0, e.pageX - container_offset.left - (size / 2)))};
    },

    _create_photo_component: function(position) {
        var $container = $('.look-container');
        return new App.Models.LookComponent().set(_.extend({width: 80,
            height: 80,
            rel_left: (position.left+40)/$container.width(),
            rel_top: (position.top+40)/$container.height()}, position));
    },

    _create_collage_component: function(product) {
        var self = this;
        var component = new App.Models.LookComponent().set({top: 0, left: 0});
        var $container = $('.look-container');
        // Load image to get width and height for look component
        var image = new Image();
        image.onload = function() {
            var width = this.width / 1.5;
            var height = this.height / 1.5;
            component.set({width: width,
                           height: height,
                           left: ($container.width() / 2) - width / 2,
                           top: ($container.height() / 2) - height / 2});

            self.add_product_to_component(component, product);
            self.model.components.add(component);
        }

        image.src = product.get('image_look');
    },
    inactivate: function() {
      App.Events.trigger("lookedit:clicked");
    },

    on_click: function(e) {

        if(!this.model.has('image') || !this.model.get('image')) {
            return true;
        }

        if(!$(e.target).hasClass('look-container')) {
            return true;
        }

        if(this.pending_product) {
            // If pending product is active (a click has occured on a product add button)
            var new_component = this._create_photo_component(this._get_hotspot(e));
            this.add_product_to_component(new_component, this.pending_product);
            this.model.components.add(new_component);
            this.pending_product = false;
            this.pending_event = false;
        } else {
            if ($(window).width() < 992) {
                this.pending_event = e;
                this.show_product_filter();
            }
        }

        // XXX: this code might be used in the future when we want to allow a
        // click in a photo without a pending product
        //} else {
            //if(this.pending_component) {
                //// If pending component is active only move it to new touch/click position
                //this.model.components.getByCid(this.pending_component).set(this._get_hotspot(e));
            //} else {
                //// Else create a new pending component on touch/click position
                //var new_component = this._create_photo_component(this._get_hotspot(e));
                //this.model.components.add(new_component);
                //this.pending_component = new_component.cid;
            //}
        //}

        this.model._dirty = true;

        e.preventDefault();
    },

    // callback for delete dialog
    delete_look: function() {
        this.model._dirty = false;
        this.model.destroy({success: function() {
            window.location.replace('/looks/');
        }});
    },

    initialize_temporary_image: function() {
        this.temporary_image_view = new App.Views.TemporaryImageUploadForm({model: this.model, look_type: external_look_type});
    },

    render: function() {
        this.$el.html(this.template({look_type: external_look_type, look: this.model.toJSON()}));

        // Reposition some stuff before adding the components
        var $container = $('.look-container');
        this.render_temporary_image();
        this.render_image();

        this.update_sizes();

        var adjust = Math.max(0, ($container.width() - this.model.get('width'))/2);
        if (adjust) {
            this.model.components.each(function(model) {model.set('left', model.get('left') + adjust)});
        }
        var adjust = Math.max(0, ($container.height() - this.model.get('height'))/2);
        if (adjust) {
            this.model.components.each(function(model) {model.set('top', model.get('top') + adjust)});
        }

        // TODO: this must be done here because it must happen after main
        // template is rendered or else it will be wiped be the above html
        // rendering call

        this.add_components(this.model.components);

        $('#product-chooser').find('.disabled').hide();
        $(window).trigger('resize');
    },

    render_temporary_image: function() {
        if(external_look_type == 'photo' && !this.model.has('image')) {
            this.$el.find('.look-container').append(this.temporary_image_view.render().el);
        }
    },

    render_image: function() {
        if(this.model.has('image')) {
            // Enable product on image
            this.init_footer();
            App.Events.trigger('product:enable');
            this.temporary_image_view.$el.hide();
            this.$el.find('.look-container').css('background-image', 'url(' + this.model.get('image') + ')');
            this.local_image = new Image();
            self = this;
            this.local_image.onload = function() {
                var image_width = this.width;
                var image_height = this.height;
                if (typeof this.naturalWidth !== 'undefined' && typeof this.naturalHeight !== 'undefined') {
                    image_width = this.naturalWidth;
                    image_height = this.naturalHeight;
                }
                self.image_ratio = image_width / image_height;
                self.model.set({image_width: image_width, image_height: image_height});
                self.update_sizes();
            }
            this.local_image.src = this.model.get('image');
        } else {
            this.disable_footer();
            this.temporary_image_view.$el.show();
            this.$el.find('.look-container').css('background-image', '');
        }
    },

    update_sizes: function() {
        // Set container height for that responsive feeling
        var window_height = $(window).height(),
            new_height = window_height - this.$el.offset().top - ($(window).width() >= 992 ? 20 : 0),
        $footer = $('.widget-footer:visible');
        new_height -= $footer.length ? $footer.height() : 0;
        this.$el.css('height', new_height);
        $container = this.$el.children('.look-container');

        // Set look type specific stuff
        if(external_look_type == 'photo' && this.model.has('image')) {
            // Set container width and height to center the image
            if (this.image_ratio) {
                if (this.image_ratio >= this.$el.width()/this.$el.height()) {
                    var new_height = Math.min(this.$el.width() / this.image_ratio, this.$el.height());
                    $container.height(new_height);
                } else {
                    var new_width = Math.min(this.$el.height() * this.image_ratio, this.$el.width());
                    $container.width(new_width);
                    $container.height(new_width / this.image_ratio);
                }

                this.model.set({width: $container.width(), height: $container.height()});
                App.Events.trigger('lookedit:rescale', {width: $container.width(), height: $container.height()});
            }
        } else {
            // Don't do stuff if area is hidden
            if (this.$el.parent().css('display') == 'none') return;
            $container.height(this.$el.height());

            // Get cropped area
            var top = right = bottom = left = -1;
            this.model.components.each(function(component) {
                var component_left = component.get('left'),
                    component_top = component.get('top');
                top = top > -1 ? Math.min(top, component_top) : component_top;
                right = right > -1 ? Math.max(right, component_left + component.get('width')) : component_left + component.get('width');
                bottom = bottom > -1 ? Math.max(bottom, component_top + component.get('height')) : component_top + component.get('height');
                left = left > -1 ? Math.min(left, component_left) : component_left;
            });

            // Reposition elements if the window is too small
            var adjustX = Math.max(right - $container.width(), 0),
                adjustY = Math.max(bottom - $container.height(), 0),
                width = right - left,
                height = bottom - top;

            this.model.set({width: width, height: height});


            if (adjustX > 0 || adjustY > 0) {
                if (adjustX > left || adjustY > top) {
                    var ratio = Math.min((Math.max(width - adjustX, $container.width()))/width, (Math.max(height - adjustY, $container.height()))/height);
                    App.Events.trigger('lookedit:rescale', ratio);
                } else {
                    App.Events.trigger('lookedit:reposition', {x: adjustX, y: adjustY});
                }
            }

        }
    },

    publish_look: function(values) {
        this.model.set('published', true);
        this.save_look(values);
    },

    unpublish_look: function() {
        this.model.set('published', false);
        this.model.save();
    },

    save_look: function(values) {
        if (values) {
            this.model.set('title', values.title);
            this.model.set('description', values.description);
        }

        if(!isAuthenticated) {
            FB.login(_.bind(function(response) {
                if(response.authResponse) {
                    data = {uid: response.authResponse.userID,
                            access_token: response.authResponse.accessToken};
                    $.post('/facebook/login', data, _.bind(function(response) {
                        this._look_save();
                    }, this));
                }
            }, this), {scope: facebook_scope});
        } else {
            this._look_save();
        }

        return false;
    },

    _look_save: function() {
        // Remove components without products before saving
        this.model.components.each(_.bind(function(model) {
            model.unset('rel_left');
            model.unset('rel_top');
            if(!model.has('product') || !model.get('product')) {
                this.model.components.remove(model);
                model.destroy();
            }
        }, this));

        if(this.model.backend == 'client') {
            this.model.backend = 'server';
            this.model.unset('id', {silent: true});
        }

        this.model.save({}, {success: _.bind(this.save_success, this)});

        // TODO: Get image data from <img> tag instead of downloading it again
        //this._image2base64(this.model.get('image'), _.bind(function(base64_image) {
            //this.model.set('image_base64', base64_image, {silent: true});
            //this.model.save({}, {success: _.bind(this.save_success, this)});
        //}, this));
    },

    save_success: function() {
        this.model._dirty = false;
        window.location.replace('/looks/' + this.model.get('slug'));
    },

    _image2base64: function(image_url, callback) {
        var canvas = document.createElement('canvas');
        var image = new Image();
        image.src = image_url;

        image.onload = function() {
            canvas.width = image.width;
            canvas.height = image.height;

            var ctx = canvas.getContext('2d');
            ctx.drawImage(image, 0, 0);
            var dataURL = canvas.toDataURL('image/png');

            callback(dataURL.replace(/^data:image\/(png|jpg);base64,/, ''));
        }
    }

});
