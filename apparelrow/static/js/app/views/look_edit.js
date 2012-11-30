App.Views.LookEdit = Backbone.View.extend({

    el: '#edit-look',
    template: _.template($('#edit_look_template').html()),

    events: {
        'click .look-container': 'look_click'
    },

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
        $('.btn-delete').on('click', _.bind(this.delete_look, this));
    },

    look_click: function(e) {
        console.log('look_click');
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
        this.temporary_image.destroy();
        this.model.clear({silent: true});
        this.model.set(_.clone(this.model.defaults), {silent: true});
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
