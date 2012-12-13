App.Views.FilterProduct = Backbone.View.extend({

    el: '#product-filter',

    events: {
        'change input[name="q"]': 'filter',
        'click input[name="q"]': 'filter',
        'keyup input[name="q"]': 'timed_filter',
        'change input[name="gender"]': 'filter',
    },

    initialize: function(options) {
        this.product_filter_model = options.product_filter_model;
        this.facets = options.facet_container;
        this.products = options.products;

        // Update filters when search product model changes
        this.product_filter_model.on('change', this.update, this);

        // Filter tabs
        this.filter_tabs = new App.Views.LookEditFilterTabs({model: this.product_filter_model});

        // Individual filters for products
        this.filter_category = new App.Views.FilterProductCategory({collection: this.facets.category, el: '#product-filter-category'});
        this.filter_subcategory = new App.Views.FilterProductSubCategory({collection: this.facets.category, el: '#product-filter-subcategory'});
        this.filter_color = new App.Views.FilterProductColor({collection: this.facets.color, el: '#product-filter-color'});
        this.filter_price = new App.Views.FilterProductPrice({collection: this.facets.price, el: '#product-filter-price'});

        // Initial fetch of products and facets
        this.facets.fetch({data: this.product_filter_model.toJSON()});
        this.products.fetch({data: this.product_filter_model.toJSON()});
    },

    update: function(e) {
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

    render: function() {
        this.filter_category.render();
        this.filter_subcategory.render();
        this.filter_color.render();
        this.filter_price.render();

        var window_height = $(window).height();
        $('#product-list').height(window_height - $('.product-list-container').offset().top - 40);
    }

});
