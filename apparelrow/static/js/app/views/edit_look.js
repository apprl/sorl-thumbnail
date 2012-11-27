App.Views.EditLook = Backbone.View.extend({

    el: '#edit-look',
    template: _.template($('#edit_look_template').html()),

    initialize: function() {
        // Initialize model, model events and fetch model
        this.model = new App.Models.Look();
        this.model.on('change', this.render, this);
        this.model.on('destroy', this.render, this);
        this.model.fetch();

        this.initialize_temporary_image();
        this.render();

        // TODO: move this to another view or expand this view
        $('.btn-reset').on('click', _.bind(this.reset, this));
        $('.btn-save').on('click', _.bind(this.save_look, this));
        $('.btn-publish').on('click', _.bind(this.publish_look, this));
    },

    reset: function() {
        // TODO: this results in two calls to render
        this.temporary_image.destroy({wait: true});
        this.model.clear();
        this.model.save();
    },

    save_look: function() {
        // TODO: force login
        if(this.model.backend == 'client') {
            this.model.backend = 'server';
            this.model.unset('id');
            this.model.save();
        }
    },

    publish_look: function() {
        if(this.model.backend == 'client') {
            this.model.backend = 'server';
            this.model.unset('id');
            this.model.set('published', true);
            this.model.save();
        }
    },

    initialize_temporary_image: function() {
        this.temporary_image = new App.Models.TemporaryImage();
        this.temporary_image_view = new App.Views.TemporaryImageUploadForm({model: this.temporary_image, look_type: external_look_type});
        this.temporary_image.on('change', this.update_temporary_image, this);
        this.temporary_image.on('destroy', this.destroy_temporary_image, this);
    },

    destroy_temporary_image: function(model) {
        this.model.unset('image');
        this.model.save();
    },

    update_temporary_image: function(model) {
        this.model.set('image', model.get('url'));
        this.model.save();
    },

    render: function() {
        console.log('render called', this.model);
        this.$el.html(this.template({look_type: external_look_type, look: this.model.toJSON()}));

        if(external_look_type == 'photo' && !this.model.get('image')) {
            if(this.hasOwnProperty('temporary_image_view')) {
                this.$el.find('.look-container').append(this.temporary_image_view.render().el);
            }
        }

        return this;
    }

});
