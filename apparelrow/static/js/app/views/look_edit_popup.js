App.Views.LookEditPopup = Backbone.View.extend({

    id: 'product-popup-container',

    events: {
        'click': 'hide'
    },

    initialize: function() {
        this.active = false;

        App.Events.on('look_edit:product:info', this.show, this);
    },

    show: function(model) {
        console.log('render a popup and show it for product with id', model.id);

        this.render(model.id);
    },

    hide: function() {
        this.$el.remove();
    },

    render: function(id) {
        this.delegateEvents();

        var chooser = $('#product-chooser');
        var offset = chooser.offset()

        this.$el.empty();
        this.$el.css({left: offset.left + 20, top: offset.top, width: chooser.width() - 20});
        this.$el.load('/products/' + id + '/popup/');
        $('body').append(this.el);
    }

});
