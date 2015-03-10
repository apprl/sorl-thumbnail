jQuery(document).ready(function() {
    // Product filter view
    window.filter_product_view = new App.Views.FilterProduct();

    // Shop create view
    window.product_widget_model   = new window.App.Models.ProductWidget();
    window.product_widget_create  = new App.Views.ProductWidgetCreate({ model: product_widget_model });

    // Router
    App.Routers.ProductWidgetCreator = Backbone.Router.extend({
        routes: {
            ':country/productwidget/create': 'product_widget_create'
        },
        product_widget_create: function() {
        }
    });

    // Initialize
    window.product_widget_create_router = new App.Routers.ProductWidgetCreator();
    Backbone.history.start({ pushState: !!(window.history && window.history.pushStage )});
});