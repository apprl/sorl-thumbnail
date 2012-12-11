App.Views.LookEditPopup = Backbone.View.extend({

    id: 'product-popup-container',

    events: {
        'click .product-popup-close': 'hide',
        'click .btn-add': 'add'
    },

    initialize: function() {
        this.active = false;

        App.Events.on('look_edit:product:info', this.show, this);
    },

    show: function(model) {
        console.log('render a popup and show it for product with id', model.id);

        $(document).on('click.popup', _.bind(function(e) {
            if($(e.target).closest('#product-popup-container').length == 0) {
                this.hide();
            }
        }, this));

        this.model = model;
        this.render(model.id);
    },

    hide: function() {
        $(document).off('click.popup');
        this.$el.remove();
    },

    add: function() {
        console.log('add lol', this.model);
        App.Events.trigger('look_edit:product:add', this.model);
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
