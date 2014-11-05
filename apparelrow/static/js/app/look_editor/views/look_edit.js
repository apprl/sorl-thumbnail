App.Views.LookEdit = App.Views.WidgetBase.extend({

    el: '#edit-look',
    template: _.template($('#edit_look_template').html()),

    events: {
        'click .look-container': 'on_click',
        'touch .look-container': 'on_click'
    },

    max_width: 694,
    max_height: 524,

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
        App.Events.on('look_edit:product:add', this.pending_add_component, this);
        this.pending_product = false;
        this.pending_component = false;

        // Listen on widget events
        App.Events.on('widget:delete', this.delete_look, this);
        App.Events.on('widget:reset', this.render, this);
        App.Events.on('widget:save', this.save_look, this);
        App.Events.on('widget:publish', this.publish_look, this);
        App.Events.on('widget:unpublish', this.unpublish_look, this);


        $(window).on('resize', _.bind(this.update_sizes, this));
        $(window).on('resize', _.bind(_.debounce(this.update_component_measures, 500), this));

        $(window).trigger('resize');

        App.Views.LookEdit.__super__.initialize(this);
    },

    update_component_measures: function() {
        $container = this.$el.find('.look-container');
        App.Events.trigger('lookedit:update_measures', {width: $container.width(), height: $container.height()});
    },

    login_popup: function() {
        this.popup_dispatcher.show('dialog_login');

        return false;
    },

    add_component: function(model, collection) {
        var view_class = this.component_view_classes[external_look_type];
        var view = new view_class({model: model, collection: collection});
        this.$('.look-container').append(view.render().el);
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
        return new App.Models.LookComponent().set(_.extend({width: 80, height: 80}, position));
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

        // TODO: this must be done here because it must happen after main
        // template is rendered or else it will be wiped be the above html
        // renderning call

        // Reposition some stuff before adding the components
        if (this.model.get('width') < this.max_width) {
            var adjust = (this.max_width - this.model.get('width'))/2;
            this.model.components.each(function(model) {model.set('left', model.get('left') + adjust)});
        }
        if (this.model.get('height') < this.max_height) {
            var adjust = (this.max_height - this.model.get('height'))/2;
            this.model.components.each(function(model) {model.set('top', model.get('top') + adjust)});
        }


        this.add_components(this.model.components);

        this.render_temporary_image();
        this.render_image();
    },

    render_temporary_image: function() {
        if(external_look_type == 'photo' && !this.model.has('image')) {
            this.$el.find('.look-container').append(this.temporary_image_view.render().el);
        }
    },

    render_image: function() {
        this.update_sizes();

        if(this.model.has('image')) {
            // Enable product on image
            App.Events.trigger('product:enable');
            this.temporary_image_view.$el.hide();
            this.$el.find('.look-container').css('background-image', 'url(' + this.model.get('image') + ')');
        } else {
            this.temporary_image_view.$el.show();
            this.$el.find('.look-container').css('background-image', '');
        }
    },

    update_sizes: function() {

        if(external_look_type == 'photo') {
            var self = this;
            this.local_image = new Image();
            this.local_image.onload = function() {
                var new_width = Math.min(self.max_width, this.width);
                var new_height = new_width / (this.width / this.height);
                if(new_height > self.max_height) {
                    var temp_height = new_height;
                    var new_height = self.max_height;
                    var new_width = (new_width / temp_height) * new_height;
                }
                new_width = Math.round(new_width);
                new_height = Math.round(new_height);

                self.$el.find('.look-container').css({width: new_width, height: new_height});
                self.$el.css({width: new_width});

                var image_width = this.width;
                var image_height = this.height;
                if(typeof this.naturalWidth !== 'undefined' && typeof this.naturalHeight !== 'undefined') {
                    image_width = this.naturalWidth;
                    image_height = this.naturalHeight;
                }
                self.model.set({width: new_width, height: new_height, image_width: image_width, image_height: image_height});
            }
            this.local_image.src = this.model.get('image');
        } else {
            var window_height = $(window).height(),
            new_height = window_height - this.$el.offset().top - 20,
            $footer = $('.widget-footer:visible');
            new_height -= $footer.length ? $footer.height() : 0;

            this.$el.css('height', new_height);
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
