jQuery(document).ready(function() {
    // Product filter view
    window.filter_product_view = new App.Views.FilterProduct();

    // Shop create view
    window.shop_model   = new window.App.Models.Shop();
    window.shop_create  = new App.Views.ShopCreate({ model: shop_model });

    // Router
    App.Routers.ShopCreator = Backbone.Router.extend({
        routes: {
            ':country/shop/create': 'shop_create'
        },
        shop_create: function() {
            console.log("SHOP_CREATE??");
        }
    });

    // Initialize
    window.shop_create_router = new App.Routers.ShopCreator();
    Backbone.history.start({ pushState: !!(window.history && window.history.pushStage )});
});