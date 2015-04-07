App.Views.CustomLinkView = Backbone.View.extend({

    id: 'custom-link-wrapper',
    className: 'product-chooser-wrapper',
    template: _.template($('#custom_link_template').html()),

    events: {
        'submit form': 'add_link'
    },

    initialize: function(options) {
        App.Events.on('look_edit:linked_placed', this.clear_form, this);
    },

    add_link: function(e) {
        var model = new Backbone.Model();
        model.set('title', this.$el.find('#id_custom_link_title').val());
        model.set('url', this.$el.find('#id_custom_link_url').val());
        e.preventDefault();
        App.Events.trigger('look_edit:add_link', model);
        return false;
    },

    clear_form: function() {
        this.$el.find('#id_custom_link_title').val('');
        this.$el.find('#id_custom_link_url').val('');
    },

    render: function() {
        this.$el.html(this.template());
        this.delegateEvents();

        return this;
    }
});
