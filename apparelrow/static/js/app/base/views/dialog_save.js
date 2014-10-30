App.Views.DialogSave = Backbone.View.extend({

    className: 'dialog-content look-save group',
    title: $('#dialog_save_template').data('title'),

    save_template: _.template($('#dialog_save_template').html()),
    publish_template: _.template($('#dialog_publish_template').html()),

    events: {
        'click .btn-cancel': 'hide',
        'click .btn-save': 'save_look',
        'click .btn-publish': 'publish_look'
    },

    initialize: function(options) {
        this.title = options.title;
    },

    publish_look: function() {
        this.model.set('published', true);
        this.save_look();
    },

    save_look: function() {
        var $title_input = this.$el.find('input[name=title]'),
            title_value = $title_input.val();

        // Validate title
        if(!title_value) {
            $title_input.css('border', '1px solid #f00');

            return false;
        }

        this.model.set('title', title_value);
        this.model.set('description', this.$el.find('textarea[name=description]').val());

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

        this.$el.html(_.template($('#look_edit_popup_loading').html())());
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
    },

    hide: function() {
        App.Events.trigger('popup_dispatcher:hide');

        return false;
    },

    render: function(name) {
        if(name == 'dialog_save') {
            this.$el.html(this.save_template(this.model.toJSON()));
        } else {
            this.$el.html(this.publish_template(this.model.toJSON()));
        }

        return this;
    }

});
