App.Views.LookEdit = Backbone.View.extend({

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

        this.initialize_temporary_image();

        this.look_edit_description = new App.Views.LookEditDescription({model: this.model});

        // Model events and fetch model
        //this.model.on('change', this.render, this);
        this.model.on('change:image', this.render_image, this);
        this.model.on('destroy', this.render, this);
        this.model.components.on('add', this.add_component, this);
        this.model.components.on('remove', this.remove_component, this);
        this.model.components.on('reset', this.add_components, this);
        // TODO: is it ok to render on error? wil it work for look edits?
        this.model.fetch({error: _.bind(function() { this.render(); }, this), success: _.bind(function() { this.render(); }, this)});

        // TODO: move this to another view or expand this view
        $('.btn-reset').on('click', _.bind(this.look_reset, this));
        $('.btn-delete').on('click', _.bind(this.look_delete, this));
        $('.btn-save').on('click', _.bind(this.look_save, this));
        $('.btn-publish').on('click', _.bind(this.look_publish, this));

        // Listen on product add
        App.Events.on('look_edit:product:add', this.pending_add_component, this);
        this.pending_product = false;
        this.pending_component = false;
    },

    add_component: function(model, collection) {
        console.log('add component', model, collection);

        var view_class = this.component_view_classes[external_look_type];
        var view = new view_class({model: model, collection: collection});
        this.$('.look-container').append(view.render().el);

        //this.pending_component = model.cid;
    },

    add_components: function(collection) {
        collection.each(_.bind(function(model) { this.add_component(model, collection); }, this));
    },

    remove_component: function(model, collection) {
        console.log('remove component', model, collection);

        // Reset pending component
        this.pending_component = false;

        this.model._dirty = true;
    },

    pending_add_component: function(product) {
        if(this.pending_component && this.model.has('image')) {
            this.model.components.getByCid(this.pending_component).set('product', product);
            this.pending_component = false;
        } else {
            this.pending_product = product;
        }
    },

    _get_hotspot: function(e) {
        var container_width = this.$el.find('.look-container').width() - 80,
            container_height = this.$el.find('.look-container').height() - 80;

        return {top: Math.min(container_height, Math.max(0, e.offsetY - 40)),
                left: Math.min(container_width, Math.max(0, e.offsetX - 40))};
    },

    _create_photo_component: function(position, product) {
        return new App.Models.LookComponent().set(_.extend({product: product}, position));
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
            var new_component = this._create_photo_component(this._get_hotspot(e), this.pending_product);
            this.model.components.add(new_component);
            this.pending_product = false;
        } else {
            if(this.pending_component) {
                // If pending component is active only move it to new touch/click position
                this.model.components.getByCid(this.pending_component).set(this._get_hotspot(e));
            } else {
                // Else create a new pending component on touch/click position
                var new_component = this._create_photo_component(this._get_hotspot(e), null);
                this.model.components.add(new_component);
                this.pending_component = new_component.cid;
            }
        }

        this.model._dirty = true;
        e.preventDefault();
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
    },

    /**
     * Look buttons
     */

    look_reset: function() {
        this.model.clear({silent: true});
        this.model.set(_.clone(this.model.defaults), {silent: true});
        this.model.components.reset([], {silent: true});
        this.model._dirty = false;
        this.model.backend = 'client';
        this.model.save();

        this.render();
    },

    look_delete: function() {
        this.model.destroy();
        window.location.replace('/looks/');
    },

    look_publish: function() {
        this.model.set('published', true);
        return this.look_save();
    },

    look_save: function() {
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
    },

    _look_save: function() {
        // Reset pending clicks on save
        this.pending_component = false;
        this.pending_product = false;

        this.model.components.each(_.bind(function(model) {
            if(!model.has('product') || !model.get('product')) {
                this.model.components.remove(model);
                model.destroy();
            }
        }, this));

        // TODO: force login
        if(this.model.backend == 'client') {
            this.model.backend = 'server';
            this.model.unset('id', {silent: true});

            // TODO: Get image data from <img> tag instead of downloading it again
            this._image2base64(this.model.get('image'), _.bind(function(base64_image) {
                this.model.set('image_base64', base64_image, {silent: true});
                this.model.save({}, {success: _.bind(this.save_success, this)});
            }, this));
        } else {
            this.model.save({}, {success: _.bind(this.save_success, this)});
        }
    },

    save_success: function() {
        this.model._dirty = false;
        window.location.replace('/looks/' + this.model.get('slug'));
    },

    initialize_temporary_image: function() {
        console.log('initialize temporary image form');
        this.temporary_image_view = new App.Views.TemporaryImageUploadForm({model: this.model, look_type: external_look_type});
    },

    render: function() {
        this.$el.html(this.template({look_type: external_look_type, look: this.model.toJSON()}));

        // TODO: this must be done here because it must happen after main
        // template is rendered or else it will be wiped be the above html
        // renderning call
        this.add_components(this.model.components);

        this.render_temporary_image();
        this.render_image();

        this.look_edit_description.setElement(this.$('.look-description')).render();
    },

    render_temporary_image: function() {
        if(external_look_type == 'photo' && !this.model.has('image')) {
            console.log('render temporary image form');
            this.$el.find('.look-container').append(this.temporary_image_view.render().el);
        }
    },

    render_image: function() {
        console.log('render image');

        this.update_width();

        if(this.model.has('image')) {
            this.temporary_image_view.$el.hide();
            this.$el.find('.look-container').css('background-image', 'url(' + this.model.get('image') + ')');
        } else {
            this.temporary_image_view.$el.show();
            this.$el.find('.look-container').css('background-image', '');
        }
    },

    update_width: function() {
        if(this.model.has('image')) {
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
                self.model.set({width: new_width, height: new_height});
            }
            this.local_image.src = this.model.get('image');
        } else {
            this.$el.find('.look-container').css({width: this.max_width, height: this.max_height});
            this.$el.css({width: this.max_width});
        }
    }

});
