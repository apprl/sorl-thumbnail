App.Views.TemporaryImageUploadForm = Backbone.View.extend({

    template: _.template($('#temporary_image_form_template').html()),

    initialize: function(options) {
        if(options.look_type == 'photo') {
            this.model.fetch();
            this.model.on('change', this.render, this);
            this.model.on('destroy', this.render, this);
            this.render();
        }
    },

    upload_done: function(e, data) {
        // Not using multiple uploads
        this.model.set(data.result[0]);
        this.model.save();
    },

    render: function() {
        this.setElement(this.template());
        this.$el.fileupload({
            done: _.bind(this.upload_done, this)
        })

        return this;
    }

});
