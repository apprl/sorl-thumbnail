App.Views.TemporaryImageUploadForm = Backbone.View.extend({

    tagName: 'div',
    id: 'image-form',
    template: _.template($('#temporary_image_form_template').html()),

    events: {
        'click .btn': 'click_button'
    },

    click_button: function(e) {
        e.preventDefault();
        this.$el.fileupload('add', {fileInput: this.$el.find('input.form-control')});
        this.$el.find('input.form-control').click();
    },

    upload_start: function(e, data) {
        this.$el.find('.loading').show();
        this.$el.find('form').hide();
    },

    upload_complete: function(e, data) {
        this.model.set('image_id', data.result[0].id);
        this.model.set('image', data.result[0].url);
        this.model._dirty = true;
    },

    render: function() {
        this.$el.html(this.template());
        this.$el.fileupload({
            submit: _.bind(this.upload_start, this),
            done: _.bind(this.upload_complete, this)
        }).find('div.upload-field').hide();

        return this;
    }

});
