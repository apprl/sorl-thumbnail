App.Views.LookEditSavePopup = Backbone.View.extend({

    id: 'popup-slim',
    save_template: _.template($('#save_look_template').html()),
    publish_template: _.template($('#publish_look_template').html()),
    popup_template: _.template($('#popup_slim_template').html()),

    events: {
        'click .close': 'hide',
        'click .btn-cancel': 'hide',
        'click .btn-save': 'save_look',
        'click .btn-publish': 'save_look'
    },

    initialize: function(options) {
        $(document).on('keydown', _.bind(function(e) { if(e.keyCode == 27) { this.hide() } }, this));

        this.$el.html(this.popup_template());
        $('body').append(this.$el);
    },

    save_look: function() {
        // TODO: validate title (other fields here?)
        var $title_input = this.$el.find('input[name=title]'),
            title_value = $title_input.val();

        if (!title_value) {
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

    show_save: function() {
        this._show();
        this.render_save();
    },

    show_publish: function() {
        this._show();
        this.render_publish();
    },

    _show: function() {
        $(document).on('click.popup', _.bind(function(e) {
            if($(e.target).closest('#popup-slim').length == 0) {
                this.hide();
            }
        }, this));
    },

    hide: function() {
        // If we hide product add popup, make sure we disable pending product also
        if(this.active_type == 'add') {
            this.parent_view.pending_product = false;
            this.active_type = false;
        }

        $(document).off('click.popup');
        this.$el.hide();

        return false;
    },

    render_publish: function() {
        this.delegateEvents();

        this.$el.find('.title').text(gettext('Publish look'));
        this.$el.find('.content').html(this.publish_template(this.model.toJSON())).addClass('look-save').addClass('group');
        this._center();
        this.$el.show();
    },

    render_save: function() {
        this.delegateEvents();

        this.$el.find('.title').text(gettext('Save look'));
        this.$el.find('.content').html(this.save_template(this.model.toJSON())).addClass('look-save').addClass('group');
        this._center();
        this.$el.show();
    },

    _center: function(){
        var width = this.$el.width();
        var height = this.$el.height();
        var chooser = $(window);
        var chooser_width = chooser.width();
        var chooser_height = chooser.height();

        this.$el.css({
            'left': (chooser_width / 2) - (width / 2),
            'top': (chooser_height / 2) - (height / 2)
        });
    }

});
