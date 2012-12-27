App.Views.LookEdit = Backbone.View.extend({

    el: '#edit-look',
    template: _.template($('#edit_look_template').html()),

    events: {
        'click .look-container': 'click',
        'touch .look-container': 'click'
    },

    initialize: function() {
        // Look component classes lookup
        this.component_view_classes = {
            'photo': App.Views.LookComponentPhoto,
            'collage': App.Views.LookComponentCollage
        };

        this.initialize_temporary_image();

        // Model events and fetch model
        //this.model.on('change', this.render, this);
        this.model.on('change:image', this.render_image, this);
        this.model.on('destroy', this.render, this);
        this.model.components.on('add', this.add_component, this);
        this.model.components.on('remove', this.remove_component, this);
        this.model.components.on('reset', this.add_components, this);
        this.model.fetch({success: _.bind(function() { this.render(); }, this)});

        // TODO: move this to another view or expand this view
        $('.btn-reset').on('click', _.bind(this.look_reset, this));
        $('.btn-delete').on('click', _.bind(this.look_delete, this));
        $('.btn-save').on('click', _.bind(this.look_save, this));
        $('.btn-publish').on('click', _.bind(this.look_publish, this));

        // Listen on product add
        App.Events.on('look_edit:product:add', this.pending_add_component, this);
        // Pending product to be added
        this.pending_product = false;
        // Pending component to receive a product
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
        _.each(collection.models, _.bind(function(model) { this.add_component(model, collection); }, this));
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

    click: function(e) {
        if(this.pending_product && this.model.has('image')) {
            // Add component to collection and render
            var component = new App.Models.LookComponent();
            component.set({
                top: e.offsetY,
                left: e.offsetX,
                product: this.pending_product
            });

            this.model.components.add(component);
            this.pending_product = false;
            this.model._dirty = true;
            e.preventDefault();
        } else if(this.model.has('image')) {
            // If pending component is created move it to new touch/click position
            if(this.pending_component) {
                console.log(this.pending_component, this.model.components, e.offsetY);
                this.model.components.getByCid(this.pending_component).set({
                    top: e.offsetY,
                    left: e.offsetX
                });
            // Else create a new pending component on touch/click position
            } else {
                var component = new App.Models.LookComponent();
                component.set({
                    top: e.offsetY,
                    left: e.offsetX,
                    product: null
                });
                this.model.components.add(component);
                this.pending_component = component.cid;
            }
            this.model._dirty = true;
            e.preventDefault();
        }
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

    redirect: function() {
        window.location.replace('/looks/' + this.model.get('slug'));
    },

    /**
     * Look buttons
     */

    look_reset: function() {
        this.model.clear({silent: true});
        this.model.set(_.clone(this.model.defaults), {silent: true});
        this.model.components.reset([], {silent: true});
        this.model.save();

        this.render();
    },

    look_delete: function() {
        this.model.destroy();

        window.location.replace('/looks/');
    },

    look_save: function() {

        // Reset pending clicks on save
        this.pending_component = false;
        this.pending_product = false;

        _.each(this.model.components.models, _.bind(function(model) {
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
                this.model.save({}, {success: _.bind(this.redirect, this)});
            }, this));
        } else {
            this.model.save({}, {success: _.bind(this.redirect, this)});
        }

    },

    look_publish: function() {
        this.model.set('published', true);

        return this.look_save();
    },

    initialize_temporary_image: function() {
        console.log('initialize temp');

        if(!this.hasOwnProperty('temporary_image_view')) {
            this.temporary_image = new App.Models.TemporaryImage();
            this.temporary_image_view = new App.Views.TemporaryImageUploadForm({model: this.temporary_image, look_type: external_look_type});
            this.temporary_image.on('change', this.update_temporary_image, this);
        }
    },

    update_temporary_image: function(model) {
        console.log('update temporary image', this.temporary_image_view);

        this.model.set('image', model.get('url'));
        this.model._dirty = true;
    },

    render: function() {
        this.$el.html(this.template({look_type: external_look_type, look: this.model.toJSON()}));

        // TODO: this must be done here because it must happen after main
        // template is rendered or else it will be wiped be the above html
        // renderning call
        this.add_components(this.model.components);

        this.render_temporary_image();
        this.render_image();
    },

    render_temporary_image: function() {
        if(external_look_type == 'photo' && !this.model.has('image')) {
            this.$('.look-container').append(this.temporary_image_view.render().el);
        }
    },

    render_image: function() {
        console.log('render image');

        if(this.model.has('image')) {
            if(this.hasOwnProperty('temporary_image_view')) {
                this.temporary_image_view.$el.hide();
            }
            this.$el.find('.look-container').css('background-image', 'url(' + this.model.get('image') + ')');
        } else {
            this.temporary_image_view.$el.show();
            this.$el.find('.look-container').css('background-image', '');
        }
    }

});
