App.Views.TemporaryImageUploadForm = Backbone.View.extend({

    template: _.template($('#temporary_image_form_template').html()),

    upload_complete: function(e, data) {
        this.model.set('image', data.result[0].url);
        this.model._dirty = true;
    },

    render: function() {
        this.setElement(this.template());
        this.$el.fileupload({
            done: _.bind(this.upload_complete, this)
        })

        return this;
    }

});
