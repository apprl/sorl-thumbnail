App.Views.FilterProduct = App.Views.WidgetBase.extend({

    el: '#product-chooser',

    events: {
        'change input[name="q"]': 'filter',
        'click input[name="q"]': 'filter',
        'keyup input[name="q"]': 'timed_filter',
        'click #product-filter-gender a': 'filter_gender',
    },

    initialize: function(options) {
        // Update facet on product filter model change
        this.product_filter_model = new App.Models.ProductFilter();
        this.product_filter_model.on('change', this.update_facet, this);
        this.product_filter_model.on('change:gender', this.update_gender, this);
        this.product_filter_model.on('change:q', this.update_search, this);

        // Product collection and view
        this.products = new App.Collections.Products();
        this.product_list = new App.Views.Products({collection: this.products, filter: this.product_filter_model});

        // Facets
        this.facets = new App.Models.FacetContainer();

        // Filter tabs
        this.filter_tabs = new App.Views.LookEditFilterTabs({model: this.product_filter_model});

        // Individual filters for products
        this.filter_category = new App.Views.FilterProductCategory({model: this.product_filter_model, collection: this.facets.category, el: '#product-filter-category'});
        this.filter_subcategory = new App.Views.FilterProductSubCategory({model: this.product_filter_model, collection: this.facets.category, el: '#product-filter-subcategory'});
        this.filter_color = new App.Views.FilterProductColor({model: this.product_filter_model, collection: this.facets.color, el: '#product-filter-color'});
        this.filter_price = new App.Views.FilterProductPrice({model: this.product_filter_model, collection: this.facets.price, el: '#product-filter-price'});

        // Product reset button
        this.filter_reset = new App.Views.FilterProductReset({model: this.product_filter_model});

        // Initial fetch of products and facets
        this.facets.fetch({data: this.product_filter_model.toJSON()});
        this.products.fetch({data: this.product_filter_model.toJSON()});

        // Product chooser enable / disable
        App.Events.on('product:enable', this.enable, this);
        App.Events.on('product:disable', this.disable, this);

        $(window).on('resize', _.bind(this.update_size, this));

        this.render();
    },

    disable: function() {
        if(!this.disabled_view) {
            var width = this.$el.outerWidth(true),
                height = this.$el.outerHeight(true);

            overlay_css = {
                'width': width,
                'height': height,
                'position': 'absolute',
                'top': 0,
                'left': 0
            };

            this.$overlay = $(this.make('div', {}));
            this.$overlay.css(overlay_css);

            this.$el.append(this.$overlay);
            this.$el.css('opacity', 0.1);

            this.disabled_view = true;
        }
    },

    enable: function() {
        if(this.disabled_view) {
            this.$overlay.remove();
            this.$el.css('opacity', 1);
            this.disabled_view = false;
        }
    },

    update_gender: function(model, value, options) {
        var checked_element = this.$el.find('input:radio[name=gender]:checked');
        if(checked_element.val() != value) {
            checked_element.removeAttr('checked');
            this.$el.find('input:radio[name=gender][value=' + value + ']').attr('checked', 'checked');
        }
    },

    update_search: function(model, value, options) {
        if(!value) {
            this.$el.find('input[name=q]').val('');
        }
    },

    update_facet: function(e) {
        this.facets.fetch({data: this.product_filter_model.toJSON()});
    },

    timed_filter: function(e) {
        if(this.timeout) {
            clearTimeout(this.timeout);
        }

        var self = this;
        this.timeout = setTimeout(function() {
            self.filter(e);
        }, 200);
    },

    filter: function(e) {
        var attr = e.currentTarget.name,
            value = e.currentTarget.value,
            currentValue = this.product_filter_model.get(attr);

        if(value == '') {
            this.product_filter_model.unset(attr);
            e.preventDefault();
            return;
        }

        // TODO: fix for click on empty search input field
        if(!(value || currentValue) || value != currentValue) {
            this.product_filter_model.set(attr, value);
        }

        e.preventDefault();
    },

    filter_gender: function(e) {
        var $target = $(e.target);
        this.$el.find('#product-filter-gender .selected').removeClass('selected');
        $target.addClass('selected');
        this.product_filter_model.set('gender', $target.data('value'));

        e.preventDefault();
    },

    render: function() {
        this.filter_category.render();
        this.filter_subcategory.render();
        this.filter_color.render();
        this.filter_price.render();

        this.update_size();
    },

    update_size: function() {
        // TODO: 40 offset?
        var window_height = $(window).height(),
            new_height = window_height - this.$el.find('.product-list-container').offset().top - 40;

        if(new_height < 220) {
            new_height = 220;
        }

        // Update product list height
        this.product_list.$el.height(new_height);
        this.product_list.$product_list_empty.height(new_height);
        this.product_list.$product_list_unauthenticated.height(new_height);

        // Update product filters
        this.filter_category.update_height(new_height);
        this.filter_subcategory.update_height(new_height);

        // If overlay is active update height
        if(this.$overlay) {
            this.$overlay.css('height', this.$el.outerHeight(true));
        }
    }

});
