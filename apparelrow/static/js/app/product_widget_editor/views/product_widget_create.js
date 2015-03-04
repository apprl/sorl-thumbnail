App.Views.ProductWidgetCreate = App.Views.WidgetBase.extend({
    el: '#product-widget-preview',
    template: _.template($('#shop_component_product').html()),

    initialize: function() {
        this.model.fetch({
            error: _.bind(function() { this.init_products(); }, this),
            success: _.bind(function() { this.init_products(); }, this)
        });

        App.Events.on('widget:delete', this.delete_product_widget, this);
        App.Events.on('widget:reset', this.reset, this);
        App.Events.on('widget:save', this.save_product_widget, this);
        App.Events.on('widget:publish', this.publish_product_widget, this);
        App.Events.on('widget:unpublish', this.unpublish_product_widget, this);
        App.Events.on('widget:product_display', this.product_display, this);

        App.Events.on('product:delete', this.resize, this);

        // Popup dispatcher
        this.popup_dispatcher = new App.Views.PopupDispatcher();
        this.popup_dispatcher.add('dialog_login', new App.Views.DialogLogin({model: this.model, dispatcher: this.popup_dispatcher}));

        // ProductWidget editor popup
        this.product_widget_edit_popup = new App.Views.ProductWidgetEditPopup({parent_view: this});

        App.Events.on('widget:product:add', this.pending_add_component, this)
        this.model.components.on('add', this.add_component, this);

        $(window).on('resize', _.bind(this.resize, this));
        $(window).on('resize onorientationchange', _.bind(this.resize, this));

        this.$el.find('.previous').on('click', _.bind(function() { this.slide(1); }, this));
        this.$el.find('.next').on('click', _.bind(function() { this.slide(-1); }, this));

        this.$container = this.$el.find('.product-list-container');

        this.$productlist = this.$el.find('#product-widget-product-list');

        var mc = new Hammer(this.$productlist[0]);
        mc.on('swipeleft swiperight', _.bind(function(e) { this.slide(e.type == 'swipeleft' ? -1 : 1); }, this));

        App.Views.ProductWidgetCreate.__super__.initialize(this);
        $(window).trigger('resize');
        $('.body-header-col-right ul').hide();
        if (this.model.get('id')) {
            $('.body-header-col-right .btn-reset').parent().hide();
        } else {
            $('.body-header-col-right .btn-delete').parent().hide();
        }
        $('#product-widget-product-list').hide();

        this.init_footer();
    },
    init_products: function() {
        if (!this.model.attributes.id) {
            $('#product-widget-display-settings').show();
            $('#product-widget-product-list').hide();
        } else {
            $('#product-widget-product-list').show();
            this.product_display(this.model.get('show_liked'));
        }
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
            this.resize();
        }
    },
    product_display: function(show_liked) {
        this.model.set('show_liked', show_liked);

        if(show_liked) {
            if (!this.model.attributes.id) {
                this.save_product_widget({ title: "My latest likes", 'callback': function() {
                    $("#embed_product_widget_form #id_name").val("My latest likes");
                    window.product_widget_create.init_products();
                }});
            }
            $('#product-widget-display-settings').find('.buttons').hide();
        } else {
            $('#product-chooser').find('.disabled').hide();
            $('#product-widget-display-settings').hide();
            $('#product-widget-product-list').removeClass('liked-products');
            $('.body-header-col-right ul').show();
            $('.body-header-col-right .btn-delete').parent().hide();
            this.init_footer();
        }
        $('#product-widget-product-list').show();
        $('#product-widget-preview').removeClass('splash');
        this.resize();
    },
    reset: function() {
        this.model.components.each(_.bind(function (model) {
            this.model.components.remove(model);
            model.destroy();
        }), this);
        this.$container.find('ul').children().remove();
    },
    resize: function() {
        var window_height = $(window).height(),
            new_height = window_height - this.$el.offset().top - 20,
        $footer = $('.widget-footer:visible');
        $header = $('#preview-header:visible')
        new_height -= ($header.length ? $header.height() + 16 : 0)+ ($footer.length ? $footer.height() : 0);
        this.$container.css('height', new_height);
        var imageratio = 1.14;
        if (this.$container.width()/this.$container.height() > imageratio) {
            this.$productlist.height(new_height*0.9).width(new_height*0.9/imageratio);
        } else {
            this.$productlist.width(this.$container.width()*0.9).height(this.$container.width()*0.9*imageratio);
        }
        this.$productlist.find('ul.product-list').width(this.model.components.length*this.$productlist.width()).css('left', '0px');
        this.$productlist.find('ul.product-list > li').width(this.$productlist.width()).height(this.$productlist.height());
    },
    pending_add_component: function(product) {
        this._create_product_component(product);
        this.resize();
    },
    _create_product_component: function(product) {
        var self = this;
        var component = new App.Models.ProductWidgetComponent();

        self.add_product_to_component(component, product);
        self.model.components.add(component);
    },
    add_product_to_component: function(component, product) {
        component.set('product', product.toJSON());
        this.model._dirty = true;
    },
    add_component: function(model, collection) {
        var view = new App.Views.ProductWidgetComponentProduct({ model: model, collection: collection });
        this.$('.product-list-container ul.product-list').append(view.render().el);
    },
    publish_product_widget: function(values) {
        this.model.set('published', true);
        this.save_product_widget(values);
    },
    unpublish_product_widget: function() {
        this.model.set('published', false);
        this.model.save();
    },
    slide: function(direction) {
        if (this.running) return;
        var $ul = this.$productlist.find('ul.product-list');
        var childwidth = $ul.parent().width();
        this.running = true;
        var newleft = $ul.position().left + direction*childwidth;

        if (newleft > 0) {
            $ul.children('li.col-product-item').last().detach().prependTo($ul);
            $ul.css('left', ($ul.position().left - childwidth) + 'px');
        } else if(newleft <= -1*$ul.width() ) {
            $ul.children('li.col-product-item').first().detach().appendTo($ul);
            $ul.css('left', ($ul.position().left + childwidth) + 'px');
        }
        var self = this;
        $ul.animate({'left': '+=' + direction*childwidth}, {'complete': function() { self.running = false; }});
    },
    delete_product_widget: function() {
        this.model._dirty = false;
        this.model.destroy({success: function() {
            window.location.replace('/productwidget/create');
        }});
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
            this._product_widget_save(values.callback);
        }

        return false;
    },

    _product_widget_save: function(callback) {
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

        this.model.save({}, {success: _.bind(function() { this.save_success(callback); }, this)});
    },

    save_success: function(callback) {
        this.model._dirty = false;
        if (callback) {
            callback(this.model.get('id'));
        } else {
            window.location.replace('/productwidget/edit/' + this.model.get('id'));
        }
    }
});