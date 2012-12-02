App.Views.LookEdit = Backbone.View.extend({

    el: '#edit-look',
    template: _.template($('#edit_look_template').html()),

    events: {
        'click .look-container': 'click',
        'touch .look-container': 'click'
    },

    // Look components classes
    component_view_classes: {
        'photo': App.Views.LookComponentPhoto,
        'collage': App.Views.LookComponentCollage
    },

    initialize: function() {
        // Initialize model, model events and fetch model
        this.model = new App.Models.Look();
        //this.model.on('change', this.render, this);
        this.model.on('change:image', this.render_image, this);
        this.model.on('destroy', this.render, this);
        this.model.components.on('add', this.add_component, this);
        this.model.components.on('remove', this.remove_component, this);
        this.model.fetch({success: _.bind(function() { this.render(); }, this)});

        // TODO: move this to another view or expand this view
        $('.btn-reset').on('click', _.bind(this.reset, this));
        $('.btn-save').on('click', _.bind(this.save_look, this));
        $('.btn-publish').on('click', _.bind(this.publish_look, this));
        $('.btn-delete').on('click', _.bind(this.delete_look, this));

        // Listen on product add
        App.Events.on('look_edit:product:add', this.pending_add_component, this);
        // Pending product to be added
        this.pending_product = false;
        // Pending component to receive a product
        this.pending_component = false;
    },

    add_component: function(model, collection) {
        console.log('add component', model, collection);
        this.model.save();

        this.pending_component = model.cid;
    },

    remove_component: function(model, collection) {
        console.log('remove component', model, collection);
        this.model.save();

        // Reset pending component
        this.pending_component = false;
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
            }
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

    reset: function() {
        if(this.hasOwnProperty('temporary_image')) {
            this.temporary_image.destroy();
            this.initialize_temporary_image();
        }
        this.model.clear({silent: true});
        //this.model.set({id: external_look_type}, {silent: true});
        this.model.set(_.clone(this.model.defaults), {silent: true});
        this.model.components.reset([], {silent: true});
        this.model.save();
    },

    delete_look: function() {
        this.model.destroy();
    },

    save_look: function() {
        // TODO: force login
        if(this.model.backend == 'client') {
            this.model.backend = 'server';
            this.model.unset('id', {silent: true});

            // TODO: Get image data from <img> tag instead of downloading it again
            this._image2base64(this.model.get('image'), _.bind(function(base64_image) {
                this.model.set('image_base64', base64_image, {silent: true});
                this.model.save();
            }, this));
        } else {
            this.model.save();
        }
    },

    publish_look: function() {
        this.model.set('published', true);

        return this.save_look();
    },

    initialize_temporary_image: function() {
        this.temporary_image = new App.Models.TemporaryImage();
        this.temporary_image_view = new App.Views.TemporaryImageUploadForm({model: this.temporary_image, look_type: external_look_type});
        this.temporary_image.on('change', this.update_temporary_image, this);
    },

    update_temporary_image: function(model) {
        this.model.set('image', model.get('url'));
        this.temporary_image_view.remove();
        this.model.save();
    },

    render: function() {
        this.$el.html(this.template({look_type: external_look_type, look: this.model.toJSON()}));

        this.render_temporary_image();
        this.render_image();
    },

    render_temporary_image: function() {
        if(external_look_type == 'photo' && !this.model.has('image')) {
            if(!this.hasOwnProperty('temporary_image_view')) {
                this.initialize_temporary_image();
            }
            this.$el.find('.look-container').append(this.temporary_image_view.render().el);
        }
    },

    render_image: function() {
        console.log('render_image');
        if(this.model.has('image')) {
            this.$el.find('.look-container').css('background-image', this.model.get('image'));
        } else {
            this.$el.find('.look-container').css('background-image', '');
        }
    },

    render_components: function() {
        if(this.hasOwnProperty('component_views')) {
            _.each(this.component_views, function(view) { view.render() });
        } else {
            this.component_views = new Array();

            _.each(this.model.components.models, _.bind(function(component) {
                var view_class;
                if(external_look_type == 'photo') {
                    view_class = App.Views.LookComponentPhoto;
                } else {
                    view_class = App.Views.LookComponentCollage;
                }
                var view = new view_class({model: component});
                this.$('.look-container').append(view.render().el);
                this.component_views.push(view);
            }, this));
        }

        // TODO: bad? must use it because this.$el is update on every render
        this.delegateEvents();

        return this;
    }

});
