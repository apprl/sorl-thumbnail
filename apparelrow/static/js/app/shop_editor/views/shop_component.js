App.Views.ShopComponent = App.Views.WidgetBase.extend({

    events: {
        'click .delete': 'on_delete',
        'mouseenter': 'on_enter',
        'mouseleave': 'on_leave'
    },

    initialize: function() {
        this.model.on('change', this.render, this);
    },

    on_delete: function(e) {
        var $title = $('#shop-product-list').find('h3');

        if($title.length) {
            var currentTitle = $title.html().split(' ');
            var newTitle = parseInt(currentTitle[0], 10) - 1 + ' ' + currentTitle[1];
            $title.html(newTitle);
        }

        this.remove();
        this.collection.remove(this.model);

        e.preventDefault();
    },

    on_enter: function(e) {
        this.$el.find('.delete').show();
    },

    on_leave: function(e) {
        this.$el.find('.delete').hide();
    },

    render: function() {
        this.$el.html(this.template(this.model.toJSON()));
        this.delegateEvents();

        return this;
    }

});
