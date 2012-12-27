App.Views.TemporaryImageUploadForm = Backbone.View.extend({

    tagName: 'div',
    id: 'image-form',
    template: _.template($('#temporary_image_form_template').html()),

    upload_start: function(e, data) {
        this.$el.find('.loading').show();
        this.$el.find('form').hide();
    },

    upload_complete: function(e, data) {
        this.model.set('image', data.result[0].url);
        this.model._dirty = true;
    },

    render: function() {
        this.$el.html(this.template());
        this.$el.fileupload({
            submit: _.bind(this.upload_start, this),
            done: _.bind(this.upload_complete, this)
        })

        return this;
    }

});
