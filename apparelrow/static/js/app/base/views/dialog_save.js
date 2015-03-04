App.Views.DialogSave = Backbone.View.extend({

    className: 'dialog-content look-save group',
    title: $('#dialog_save_template').data('title'),

    save_template: _.template($('#dialog_save_template').html()),
    publish_template: _.template($('#dialog_publish_template').html()),

    events: {
        'click .btn-cancel': 'hide',
        'click .btn-save': 'save',
        'click .btn-publish': 'publish'
    },

    initialize: function(options) {
        this.title = options.title;
        this.model = options.model
    },

    save: function() {
        if (this._prepare_save()) {
            App.Events.trigger('widget:save', {title: this.title, description: this.description});
        }
    },

    publish: function() {
        if (this._prepare_save()) {
            App.Events.trigger('widget:publish', {title: this.title, description: this.description});
        }
    },

    _prepare_save: function() {
        var $title_input = this.$el.find('input[name=title]'),
           title_value = $title_input.val();

        // Validate title
        if(!title_value) {
            $title_input.css('border', '1px solid #f00');
            return false;
        }

        this.title = title_value;
        this.description = this.$el.find('#look_description').val();

        this.$el.html(_.template($('#look_edit_popup_loading').html())());
        return true;
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
