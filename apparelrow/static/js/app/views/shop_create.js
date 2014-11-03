App.Views.ShopCreate = App.Views.WidgetBase.extend({
    el: '#shop-preview',
    template: _.template($('#shop_component_product').html()),
    initialize: function() {
        this.model.fetch({
            error: _.bind(function() { this.init_products(); }, this),
            success: _.bind(function() { this.init_products(); }, this)
        });

        App.Events.on('look_edit:product:add', this.pending_add_component, this)
        this.model.components.on('add', this.add_component, this);
    },
    init_products: function() {
        for(var i = 0; i < this.model.attributes.products.length; i++) {
            var product = this.model.attributes.products[i];
            var self = this;
            var component = new App.Models.ShopComponent();
            component.set('product', product);
            self.model.components.add(component);
        }
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
        var view = new App.Views.ShopComponentProduct({ model: model, collection: collection });
        this.$('#shop-product-list').append(view.render().el);
    }
});