App.Views.ProductWidgetCreate = App.Views.WidgetBase.extend({
    el: '#product-widget-preview',
    template: _.template($('#shop_component_product').html()),
    indexes: [],
    current_index: 0,
    allowprev: false,
    allownext: false,

    initialize: function() {
        this.model.fetch({
            error: _.bind(function() { this.init_products(); }, this),
            success: _.bind(function() { this.init_products(); }, this)
        });

        App.Events.on('widget:delete', this.delete_product_widget, this);
        App.Events.on('widget:reset', this.reset, this);
        App.Events.on('widget:save', this.save_product_widget, this);
        App.Events.on('widget:product_display', this.product_display, this);
        App.Events.on('widget:touchmenu', this.alter_buttons, this);
        App.Events.on('product:delete', function() {
            this.indexes.splice(this.indexes.indexOf(this.current_index), 1);
            for (var i=0; i<this.indexes.length; i++) {
                if (this.indexes[i] > this.current_index) this.indexes[i]--;
            }
            if (this.current_index > 0) {
                this.current_index--;
            }
            this.update_title(-1);
            this.resize();
        }, this);

        // Popup dispatcher
        this.popup_dispatcher = new App.Views.PopupDispatcher();
        this.popup_dispatcher.add('dialog_login', new App.Views.DialogLogin({model: this.model, dispatcher: this.popup_dispatcher}));
        this.popup_dispatcher.add('dialog_no_products', new App.Views.DialogNoProducts({model: this.model, dispatcher: this.popup_dispatcher}));
        this.popup_dispatcher.add('dialog_few_products', new App.Views.DialogFewProducts({model: this.model, dispatcher: this.popup_dispatcher}));


        var self = this;
        $(window).on('show.bs.modal', function(e) {
            if ($(e.relatedTarget).hasClass('btn-embed') && self.model.components.length < 3 && external_product_widget_type == 'multiple') {
                self.popup_dispatcher.show('dialog_few_products');
                return e.preventDefault();
            }
        });

        this.num_multi = 3;
        this.list_width_factor = 0.8;

        // ProductWidget editor popup
        this.product_widget_edit_popup = new App.Views.ProductWidgetEditPopup({parent_view: this});

        App.Events.on('widget:product:add', this.pending_add_component, this);

        this.model.components.on('add', this.add_component, this);

        $(window).on('resize', _.bind(this.resize, this));
        $(window).on('resize onorientationchange', _.bind(this.resize, this));

        this.$el.find('.previous').on('click', _.bind(function() { this.slide(1); }, this));
        this.$el.find('.next').on('click', _.bind(function() { this.slide(-1); }, this));

        this.$container = this.$el.find('.product-list-container');

        this.$productlist = this.$el.find('#product-widget-product-list');

        var mc = new Hammer(this.$productlist[0]);
        mc.on('swipeleft swiperight', _.bind(function(e) { this.slide(e.type == 'swipeleft' ? -1 : 1); }, this));

        this.$controls = [this.$el.find('.previous'), this.$el.find('.next')];

        App.Views.ProductWidgetCreate.__super__.initialize(this);

        $('.body-header-col-right ul').hide();
        $(window).trigger('resize');

        $('#product-widget-product-list').hide();
    },
    init_products: function() {
        if (!this.model.attributes.id) {
            $('#product-widget-display-settings').show();
        } else {
            this.product_display(this.model.get('show_liked'));
        }
        $('.body-header-col-right ul').show();

        if (this.model.get('show_liked')) {
            $('#modal_embed_product_widget #id_name').parent().hide();
            $('.body-header-col-right .btn-embed').click();
        }
        $('.body-header-col-right .btn-delete').parent().show();
        $('.body-header-col-right .btn-reset').parent().hide();
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
        this.init_footer();
        if(show_liked) {
            if (!this.model.attributes.id) {
                this.save_product_widget({ title: "My liked products", 'callback': function(id) {
                    $("#embed_product_widget_form #id_name").val("My liked products");
                    window.product_widget_create.init_products();
                    external_product_widget_id = id;
                }});
            }
            $('body').addClass('show-liked');
            $('.widget-footer .btn-add-item').prop('disabled', true);
            $('#modal_embed_product_widget .modal-footer').find('.btn.hidden').removeClass('hidden');
            $('#modal_embed_product_widget .modal-footer').find('.btn:first').addClass('hidden');
            $('#product-chooser .disabled .info').show();
            $('#product-widget-display-settings').find('.buttons').hide();
        } else {
            $('#product-chooser').find('.disabled').hide();
            $('#product-widget-display-settings').hide();
            $('#product-widget-product-list').removeClass('liked-products');
            $('.body-header-col-right ul').show();
            $('.body-header-col-right .btn-delete').parent().hide();
        }
        $('#product-widget-product-list').show();
        $('#product-widget-preview').removeClass('splash');
        this.resize();
    },
    update_title: function(delta, val) {
        var $title = this.$el.find('#preview-header');
        var nr = parseInt(/\d+/.exec($title.html()), 10);
        val = val == undefined ? nr + delta : val;

        $title.html($title.html().replace(nr, val));
    },
    toggle_navigation: function() {
        $ul = this.$productlist.find('ul.product-list');
        if (external_product_widget_type == 'single') {
            if (this.model.components.length > 0) {
                var index = this.indexes.indexOf(this.current_index);
                this.allownext = index < this.indexes.length-1;
                this.allowprev = index > 0;
                $('.previous, .next').toggle(true);
            } else {
                $('.previous, .next').toggle(false);
            }
        } else {
            if (this.model.components.length > this.num_multi) {
                var childwidth = $ul.parent().width()/this.num_multi;
                this.allownext = Math.round(($ul.width()+$ul.position().left)/childwidth) > this.num_multi;
                this.allowprev = Math.round($ul.position().left) != 0;
                 $('.previous, .next').toggle(true);
            } else {
                $('.previous, .next').toggle(false);
            }
        }
    },
    reset: function() {
        this.model.components.each(_.bind(function (model) {
            this.model.components.remove(model);
            model.destroy();
        }), this);
        this.$container.find('ul').children().remove();
        this.update_title(0, 0);
    },
    resize: function() {
        $footer = $('.widget-footer:visible');
        $header = $('#preview-header:visible')
        var window_height = $(window).height(),
            new_height = window_height - this.$el.offset().top -
                ($header.length ? $header.height() + 18 : 0) - ($footer.length ? $footer.height() : 18),
            imageratio = 1,
            controlpos;

        this.num_multi = this.$container.width() <= 480 ? 2 : 3;
        this.$container.css('height', new_height);

        if (external_product_widget_type == 'single') {
            if (this.$container.width()/this.$container.height() > imageratio) {
                this.$productlist.height(new_height*this.list_width_factor).width(new_height*this.list_width_factor/imageratio);
            } else {
                this.$productlist.width(this.$container.width()*this.list_width_factor).height(this.$container.width()*imageratio);
            }
            this.$productlist.find('ul.product-list').width(this.model.components.length*this.$productlist.width()).css('left', -1*this.indexes.indexOf(this.current_index)*this.$productlist.width());
            this.$productlist.find('ul.product-list img.fake-product-image').width(this.$productlist.width()).height(this.$productlist.height());
            controlpos = Math.max(5, (this.$container.width() - this.$productlist.width())/2 - this.$controls[0].width());
        } else {
            if (this.$container.width()/this.$container.height() > this.num_multi*imageratio) {
                this.$productlist.height(new_height*this.list_width_factor).width(this.num_multi*new_height*this.list_width_factor/imageratio);
            } else {
                this.$productlist.width(this.$container.width()*this.list_width_factor).height(this.$container.width()*imageratio/this.num_multi);
            }
            this.$productlist.find('ul.product-list').width(this.model.components.length*this.$productlist.width()/this.num_multi);
            this.$productlist.find('ul.product-list img.fake-product-image').width(this.$productlist.width()/this.num_multi).height(this.$productlist.height());
            if (this.model.components.length > this.num_multi) {
                this.$productlist.find('ul.product-list').css('left',  Math.max(-1*(this.indexes.length-this.num_multi)*this.$productlist.width()/this.num_multi, -1*this.indexes.indexOf(this.current_index)*this.$productlist.width()/this.num_multi));
            } else {
                this.$productlist.find('ul.product-list').css('left', 0);
            }

            controlpos = Math.max(5, (this.$container.width() - this.$productlist.width())/2 - this.$controls[0].width());
        }
        this.$controls[0].css('left', controlpos-10);
        this.$controls[1].css('right', controlpos-10);
        this.toggle_navigation();
    },
    highlight_last: function() {
        var $ul = this.$productlist.find('ul.product-list');
        var childwidth = $ul.parent().width();
    },
    pending_add_component: function(product) {
        this._create_product_component(product);
        this.current_index = this.indexes.length-1;
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
        var i;
        if (!this.indexes.length) {
            this.indexes.push(0);
            i=0;
        } else {
            i = this.indexes.indexOf(this.indexes.length - 1);
            this.indexes.splice(i+1, 0, this.indexes.length);
        }
        if (this.indexes.length == 1) {
            this.$('.product-list-container ul.product-list').append(view.render().el);
        } else {
            this.$('.product-list-container ul.product-list li.col-product-item:eq('+i+')').after(view.render().el);
        }
        this.update_title(1);
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
        if (direction == 1 && !this.allowprev) return;
        if (direction == -1 && !this.allownext) return;
        var $ul = this.$productlist.find('ul.product-list');
        var childwidth = $ul.parent().width();
        if (external_product_widget_type == 'multiple') {
            childwidth = childwidth/this.num_multi;
        }
        this.running = true;
        var newleft = $ul.position().left + direction*childwidth;
        var i = this.indexes.indexOf(this.current_index) - direction;

        this.current_index = this.indexes[i];

        var self = this;
        $ul.animate({'left': '+=' + direction*childwidth}, {'complete': function() {self.toggle_navigation(); self.running = false; }});
    },
    delete_product_widget: function() {
        this.model._dirty = false;
        this.model.destroy({success: function() {
            window.location.replace(external_widget_url);
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