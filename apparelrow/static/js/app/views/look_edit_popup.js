App.Views.LookEditPopup = Backbone.View.extend({

    id: 'popup-slim',
    template: _.template($('#look_edit_add_popup_template').html()),

    popup_template: _.template($('#popup_slim_template').html()),

    events: {
        'click .close': 'hide',
        'click .btn-add': 'add_product'
    },

    initialize: function(options) {
        this.parent_view = options.parent_view;

        App.Events.on('look_edit:product:info', this.product_info, this);
        App.Events.on('look_edit:product:add', this.product_add, this);

        $(document).on('keydown', _.bind(function(e) { if(e.keyCode == 27) { this.hide() } }, this));

        this.$el.html(this.popup_template());
        $('body').append(this.$el);
    },

    product_info: function(model) {
        this.active_type = 'info';
        this.show(model);
        this.render_info();
    },

    product_add: function(model) {
        // Do not show add product popup if we have a pending component waiting
        // for this click or if the look type is collage
        if(!this.parent_view.pending_component && external_look_type == 'photo') {
            this.active_type = 'add';
            this.show(model);
            this.render_add();
        } else if(external_look_type == 'collage') {
            this.hide();
        }
    },

    show: function(model) {
        this.model = model;

        $(document).on('click.popup', _.bind(function(e) {
            if($(e.target).closest('#popup-slim').length == 0) {
                this.hide();
            }
        }, this));
    },

    hide: function() {
        // If we hide product add popup, make sure we disable pending product also
        if(this.active_type == 'add') {
            this.parent_view.pending_product = false;
            this.active_type = false;
        }

        $(document).off('click.popup');
        this.$el.hide();

        App.Events.trigger('product:enable');

        return false;
    },

    add_product: function() {
        App.Events.trigger('look_edit:product:add', this.model);

        return false;
    },

    render_info: function() {
        App.Events.trigger('product:disable');

        this.delegateEvents();

        var url = '/products/' + this.model.get('id') + '/popup/';
        // TODO: why this width?
        this.$el.css('width', 594);
        this.$el.find('.title').text(gettext('Product info'));
        var content = this.$el.find('.content');
        content.empty();
        content.html(_.template($('#look_edit_popup_loading').html())());
        content.addClass('center');
        content.load(url, _.bind(function() {
            content.removeClass('center');
            this._center();
        }, this));

        this._center();
        this.$el.show();
    },

    render_add: function() {
        App.Events.trigger('product:disable');

        this.delegateEvents();

        this.$el.find('.title').text(gettext('Add product'));
        this.$el.find('.content').html(this.template(this.model.toJSON()));
        this.$el.css('width', 'auto');
        this._center();
        this.$el.show();
    },

    _center: function(){
        var width = this.$el.width();
        var height = this.$el.height();
        var chooser = $('#product-chooser');
        var chooser_width = chooser.width();
        var chooser_height = chooser.height();
        var offset = chooser.offset();

        var left = offset.left + 20 + (chooser_width / 2) - (width / 2);
        if(left + width > $(window).width()) {
            left = $(window).width() - width - 20;
        }

        this.$el.css({
            'left': left,
            'top': offset.top + (chooser_height / 2) - (height / 2)
        });
    }

});
