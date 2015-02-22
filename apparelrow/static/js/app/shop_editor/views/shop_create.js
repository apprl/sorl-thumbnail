App.Views.ShopCreate = App.Views.WidgetBase.extend({
    el: '#shop-preview',
    template: _.template($('#shop_component_product').html()),

    initialize: function() {
        this.model.fetch({
            error: _.bind(function() { this.init_products(); }, this),
            success: _.bind(function() { this.init_products(); }, this)
        });

        App.Events.on('widget:delete', this.delete_shop, this);
        App.Events.on('widget:reset', this.reset, this);
        App.Events.on('widget:save', this.save_shop, this);
        App.Events.on('widget:publish', this.publish_shop, this);
        App.Events.on('widget:unpublish', this.unpublish_shop, this);
        App.Events.on('widget:product_display', this.product_display, this);

        // Popup dispatcher
        this.popup_dispatcher = new App.Views.PopupDispatcher();
        this.popup_dispatcher.add('dialog_login', new App.Views.DialogLogin({model: this.model, dispatcher: this.popup_dispatcher}));

        // Shop editor popup
        this.shop_edit_popup = new App.Views.ShopEditPopup({parent_view: this});

        App.Events.on('widget:product:add', this.pending_add_component, this)
        App.Events.on('product:delete', function() { this.update_title(-1); }, this);
        this.model.components.on('add', this.add_component, this);

        $(window).on('resize', _.bind(this.resize, this));
        $(window).on('resize onorientationchange', _.bind(this.resize, this));

        this.$container = this.$el.find('.product-list-container');

        App.Views.ShopCreate.__super__.initialize(this);
        $('.body-header-col-right ul').hide();
        $(window).trigger('resize');
    },
    init_products: function() {
        if (!this.model.attributes.id) {
            $('#shop-display-settings').show();
        } else {
            this.product_display(this.model.get('show_liked'));
        }
        $('.body-header-col-right ul').show();

        if (this.model.get('show_liked')) {
            $('#modal_embed_shop #id_name').parent().hide();
            $('.body-header-col-right .btn-embed').click();
        }
        $('.body-header-col-right .btn-delete').parent().show();
        $('.body-header-col-right .btn-reset').parent().hide();
        if(this.model.attributes.hasOwnProperty('products')) {
            for (var i = 0; i < this.model.attributes.products.length; i++) {
                var product = this.model.attributes.products[i];
                var self = this;
                var component = new App.Models.ShopComponent();
                if (product.discount_price == null) {
                    product.discount_price = 0;
                }
                component.set('product', product);
                self.model.components.add(component);
            }
        }
        $(window).trigger('resize');
    },
    reset: function() {
        this.model.components.each(_.bind(function(model) {
            this.model.components.remove(model);
            model.destroy();
        }), this);
        this.update_title(0, 0);
        this.$container.find('ul').children().remove();
    },
    resize: function() {
        var window_height = $(window).height(),
            new_height = window_height - this.$el.offset().top - ($(window).width() >= 992 ? 20 : 0),
        $footer = $('.widget-footer:visible');
        new_height -= $footer.length ? $footer.height() : 0;
        this.$container.css('height', new_height);
    },
    pending_add_component: function(product) {
        this._create_product_component(product);
    },
    _create_product_component: function(product) {
        var self = this;
        var component = new App.Models.ShopComponent();
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
        var view = new App.Views.ShopComponentProduct({ model: model, collection: collection });
        this.$('#shop-product-list .product-list').append(view.render().el);
    },
    update_title: function(delta, val) {
        var $title = this.$el.find('#preview-header');
        var nr = parseInt(/\d+/.exec($title.html()), 10);
        val = val == undefined ? nr + delta : val;

        $title.html($title.html().replace(nr, val));
    },
    publish_shop: function(values) {
        this.model.set('published', true);
        this.save_shop(values);
    },
    product_display: function(show_liked) {
        this.model.set('show_liked', show_liked);

        if(show_liked) {
            if (!this.model.attributes.id) {
                this.save_shop({ title: "My latest likes", 'callback': function() {
                    console.log(window.shop_create);
                    window.shop_create.init_products();
                }});
            }
            $('#shop-display-settings').find('.buttons').hide();
        } else {
            $('#product-chooser').find('.disabled').hide();
            $('#shop-display-settings').hide();
            $('#shop-product-list').removeClass('liked-products');
            $('.body-header-col-right ul').show();
            $('.body-header-col-right .btn-delete').parent().hide();
            this.init_footer();
        }
        $('#shop-preview').removeClass('splash');
        this.resize();
    },
    unpublish_shop: function() {
        this.model.set('published', false);
        this.model.save();
    },
    delete_shop: function() {
        this.model._dirty = false;
        this.model.destroy({success: function() {
            window.location.replace('/shop/create');
        }});
    },
    save_shop: function(values) {
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
            this._shop_save(values.callback);
        }

        return false;
    },

    _shop_save: function(callback) {
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

        this.model.save({}, {success: _.bind(function() { this.save_success(callback);}, this)});
    },

    save_success: function(callback) {
        this.model._dirty = false;
        // TODO: Can we get this value from elsewhere?
        if (callback) {
            callback(this.model.get('id'));
        } else {
            window.location.replace(external_shops_url);
        }
    }
});