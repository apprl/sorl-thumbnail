App.Views.LookEditPopup = Backbone.View.extend({

    id: 'product-popup-container',
    template: _.template($('#look_edit_add_popup_template').html()),

    events: {
        'click .popup-close': 'hide',
        'click .btn-add': 'add'
    },

    initialize: function() {
        this.active = false;

        App.Events.on('look_edit:product:info', this.product_info, this);
        App.Events.on('look_edit:product:add', this.product_add, this);
    },

    product_info: function(model) {
        this.show(model);
        this.render_info();
    },

    product_add: function(model) {
        this.show(model);
        this.render_add();
    },

    show: function(model) {
        this.model = model;

        $(document).on('click.popup', _.bind(function(e) {
            console.log($(e.target), $(e.target).closest('#product-popup-container'));
            if($(e.target).closest('#product-popup-container').length == 0) {
                this.hide();
            }
        }, this));
    },

    hide: function() {
        $(document).off('click.popup');
        this.$el.remove();

        return false;
    },

    add: function() {
        App.Events.trigger('look_edit:product:add', this.model);

        this.render_add();

        return false;
    },

    render_info: function() {
        this.delegateEvents();

        var chooser = $('#product-chooser');
        var offset = chooser.offset()

        this.$el.empty();
        this.$el.css({left: offset.left + 20,
                      top: offset.top,
                      width: chooser.width() - 20,
                      height: 3 * ($('#product-tabs').outerHeight(true) + $('#product-filter').outerHeight(true))});
        // TODO: loader icon
        this.$el.load('/products/' + this.model.get('id') + '/popup/');
        $('body').append(this.el);
    },

    render_add: function() {

        console.log('render _addd');
        var chooser = $('#product-chooser');
        var offset = chooser.offset()

        console.log(this.model);

        this.$el.html(this.template(this.model.toJSON()));
        this.$el.css({left: offset.left + 20,
                      top: offset.top,
                      width: chooser.width() - 20,
                      height: $('#product-tabs').outerHeight(true) + $('#product-filter').outerHeight(true) - 20});
        $('body').append(this.el);

        this.delegateEvents();
    }

});
