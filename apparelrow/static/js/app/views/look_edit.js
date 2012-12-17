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

        // Popup dispatcher
        this.popup_dispatcher = new App.Views.PopupDispatcher();
        this.popup_dispatcher.add('dialog_reset', new App.Views.DialogReset({model: this.model}));
        this.popup_dispatcher.add('dialog_delete', new App.Views.DialogDelete({model: this.model}));
        this.popup_dispatcher.add('dialog_unpublish', new App.Views.DialogUnpublish({model: this.model}));

        // Look editor popup
        this.look_edit_popup = new App.Views.LookEditPopup({parent_view: this});
        this.look_edit_save_popup = new App.Views.LookEditSavePopup({model: this.model});

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

        // TODO: move this to another view or expand this view
        $(document).on('click', '.btn-reset', _.bind(this.look_reset, this));
        $(document).on('click', '.btn-delete', _.bind(this.look_delete, this));
        $(document).on('click', '.btn-save', _.bind(this.look_save, this));
        $(document).on('click', '.btn-publish', _.bind(this.look_publish, this));
        $(document).on('click', '.btn-unpublish', _.bind(this.look_unpublish, this));

        this.model.on('change:published', function(model, value, options) {
            if(value === false) {
                var $button = $('.btn-unpublish');
                $button.text($button.data('publish-text')).addClass('btn-publish').removeClass('btn-unpublish');
            }
        }, this);

        // Render look edit view on custom look reset event
        App.Events.on('look:reset', this.render, this);

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

        // Reset product selection
        App.Events.trigger('product:reset');
    },

    pending_add_component: function(product) {
        if(this.pending_component && this.model.has('image')) {
            this.add_product_to_component(this.model.components.getByCid(this.pending_component), product);
            this.pending_component = false;
        } else {
            if(external_look_type == 'collage') {
                this._create_collage_component(product);
            } else {
                this.pending_product = product;
            }
        }
    },

    _get_hotspot: function(e) {
        // TODO: maybe use dynamic scale for hotspot size instead of 80x80
        var container_width = this.$el.find('.look-container').width() - 80,
            container_height = this.$el.find('.look-container').height() - 80;

        return {top: Math.min(container_height, Math.max(0, e.offsetY - 40)),
                left: Math.min(container_width, Math.max(0, e.offsetX - 40))};
    },

    _create_photo_component: function(position) {
        return new App.Models.LookComponent().set(_.extend({width: 80, height: 80}, position));
    },

    _create_collage_component: function(product) {
        var self = this;
        var component = new App.Models.LookComponent().set({top: 0, left: 0});

        // Load image to get width and height for look component
        var image = new Image();
        image.onload = function() {
            component.set({width: this.width / 1.5, height: this.height / 1.5});
            self.add_product_to_component(component, product);
            self.model.components.add(component);
        }
        image.src = product.get('image_medium');
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
        } else {
            if(this.pending_component) {
                // If pending component is active only move it to new touch/click position
                this.model.components.getByCid(this.pending_component).set(this._get_hotspot(e));
            } else {
                // Else create a new pending component on touch/click position
                var new_component = this._create_photo_component(this._get_hotspot(e));
                this.model.components.add(new_component);
                this.pending_component = new_component.cid;
            }
        }

        this.model._dirty = true;
        e.preventDefault();
    },

    /**
     * Look buttons
     */

    look_reset: function() {
        this.popup_dispatcher.show('dialog_reset');

        return false;
    },

    look_delete: function() {
        this.popup_dispatcher.show('dialog_delete');

        return false;
    },

    look_publish: function() {
        this.model.set('published', true);
        this.look_edit_save_popup.show_publish();

        return false;
    },

    look_unpublish: function() {
        this.popup_dispatcher.show('dialog_unpublish');

        return false;
    },

    look_save: function() {
        this.look_edit_save_popup.show_save();

        return false;
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
    },

    render_temporary_image: function() {
        if(external_look_type == 'photo' && !this.model.has('image')) {
            console.log('render temporary image form');
            this.$el.find('.look-container').append(this.temporary_image_view.render().el);
        }
    },

    render_image: function() {
        console.log('render image');

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
