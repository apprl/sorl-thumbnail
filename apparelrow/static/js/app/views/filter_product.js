App.Views.FilterProduct = Backbone.View.extend({

    el: '#product-filter',

    events: {
        'change input[name="q"]': 'filter',
        'click input[name="q"]': 'filter',
        'keyup input[name="q"]': 'timed_filter',
        'change input[name="gender"]': 'filter',
    },

    initialize: function(options) {
        this.search_product = options.search_product;
        this.facets = options.facet_container;
        this.products = options.products;

        // Update filters when search product model changes
        this.search_product.on('change', this.update, this);

        // Initial fetch of facets
        this.facets.fetch({data: this.search_product.toJSON()});

        // Filter tabs
        this.filter_tabs = new App.Views.LookEditFilterTabs({model: this.search_product});

        // Individual filters for products
        this.filter_category = new App.Views.FilterProductCategory({collection: this.facets.category});

        this.filter_color = new App.Views.FilterProductColor({collection: this.facets.color});
        this.filter_color.render();

        this.filter_price = new App.Views.FilterProductPrice({collection: this.facets.price});
        this.filter_price.render();

        this.$el.find('.sub-filters').append(this.filter_category.el, this.filter_color.el, this.filter_price.el);

        // TODO: fix remaining filters
        //this.filter_manufacturer = new App.Views.FilterProductManufacturer({collection: this.facets.manufacturer});
    },

    update: function(e) {
        this.facets.fetch({data: this.search_product.toJSON()});
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
            currentValue = this.search_product.get(attr);

        if(value == '') {
            this.search_product.unset(attr);
            e.preventDefault();
            return;
        }

        // TODO: fix for click on empty search input field
        if(!(value || currentValue) || value != currentValue) {
            this.search_product.set(attr, value);
        }

        e.preventDefault();
    },

    render: function() {
        this.filter_category.setElement(this.$('#product-filter-category')).render();
    }

});
