App.Views.ProductWidgetCreate = App.Views.WidgetBase.extend({
    el: '#product-widget-preview',
    template: _.template($('#shop_component_product').html()),

    initialize: function() {
        this.model.fetch({
            error: _.bind(function() { this.init_products(); }, this),
            success: _.bind(function() { this.init_products(); }, this)
        });

        App.Events.on('widget:delete', this.delete_product_widget, this);
        App.Events.on('widget:reset', this.render, this);
        App.Events.on('widget:save', this.save_product_widget, this);
        App.Events.on('widget:publish', this.publish_product_widget, this);
        App.Events.on('widget:unpublish', this.unpublish_product_widget, this);

        // Popup dispatcher
        this.popup_dispatcher = new App.Views.PopupDispatcher();
        this.popup_dispatcher.add('dialog_login', new App.Views.DialogLogin({model: this.model, dispatcher: this.popup_dispatcher}));

        // ProductWidget editor popup
        this.product_widget_edit_popup = new App.Views.ProductWidgetEditPopup({parent_view: this});

        App.Events.on('widget:product:add', this.pending_add_component, this)
        this.model.components.on('add', this.add_component, this);

        $(window).on('resize', _.bind(this.resize, this));

        this.$container = this.$el.find('.product-list-container');
        $('#product-chooser').find('.disabled').hide();
        this.resize();
        App.Views.ProductWidgetCreate.__super__.initialize(this);
    },
    init_products: function() {
        if(this.model.attributes.hasOwnProperty('products')) {
            for (var i = 0; i < this.model.attributes.products.length; i++) {
                var product = this.model.attributes.products[i];
                var self = this;
                var component = new App.Models.ProductWidgetComponent();
                if (product.discount_price == null) {
                    product.discount_price = 0;
                }
                component.set('product', product);
                self.model.components.add(component);
            }
        }
    },
    resize: function() {
        var window_height = $(window).height(),
            new_height = window_height - this.$el.offset().top - 20,
        $footer = $('.widget-footer:visible');
        $header = $('#preview-header:visible')
        new_height -= ($header.length ? $header.height() + 16 : 0)+ ($footer.length ? $footer.height() : 0);
        this.$container.css('height', new_height);
    },
    pending_add_component: function(product) {
        this._create_product_component(product);
    },
    _create_product_component: function(product) {
        var self = this;
        var component = new App.Models.ProductWidgetComponent();
        var $container = $('#shop-product-list');

        self.add_product_to_component(component, product);
        self.model.components.add(component);
    },
    add_product_to_component: function(component, product) {
        component.set('product', product.toJSON());
        this.model._dirty = true;
    },
    add_component: function(model, collection) {
        this.update_title(1);
        var view = new App.Views.ProductWidgetComponentProduct({ model: model, collection: collection });
        this.$('#shop-product-list .product-list').append(view.render().el);
    },
    update_title: function(delta) {
        var $title = $('#shop-product-list').find('h3');
        var currentTitle = $title.html().split(' ');
        var newTitle = parseInt(currentTitle[0], 10) + delta +' '+ currentTitle[1];
        $title.html(newTitle);
    },
    publish_product_widget: function(values) {
        this.model.set('published', true);
        this.save_product_widget(values);
    },
    unpublish_product_widget: function() {
        this.model.set('published', false);
        this.model.save();
    },

    save_product_widget: function(values) {
        if (values) {
            this.model.set('title', values.title);
            this.model.set('description', values.description);
        }

        if(!isAuthenticated) {
            FB.login(_.bind(function(response) {
                if(response.authResponse) {
                    data = {uid: response.authResponse.userID,
                            access_token: response.authResponse.accessToken};
                    $.post('/facebook/login', data, _.bind(function(response) {
                        this._look_save();
                    }, this));
                }
            }, this), {scope: facebook_scope});
        } else {
            this._product_widget_save();
        }

        return false;
    },

    _product_widget_save: function() {
        // Remove components without products before saving
        this.model.components.each(_.bind(function(model) {
            if(!model.has('product') || !model.get('product')) {
                this.model.components.remove(model);
                model.destroy();
            }
        }, this));

        if(this.model.backend == 'client') {
            this.model.backend = 'server';
            this.model.unset('id', {silent: true});
        }

        this.model.save({}, {success: _.bind(this.save_success, this)});
    },

    save_success: function() {
        this.model._dirty = false;
        window.location.replace('/productwidget/edit/' + this.model.get('id'));
    }
});