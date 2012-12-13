jQuery(document).ready(function() {
    window.product_filter_model = new App.Models.ProductFilter();
    window.products = new App.Collections.Products();
    window.facet_container = new App.Models.FacetContainer();
    window.product_list = new App.Views.Products({collection: products, filter: product_filter_model});
    window.filter_product = new App.Views.FilterProduct({product_filter_model: product_filter_model,
                                                         products: products,
                                                         facet_container: facet_container});
    filter_product.render();

    // Look edit view
    window.look_model = new App.Models.Look();
    window.look_edit = new App.Views.LookEdit({model: look_model});

    // Look editor popup
    window.look_edit_popup = new App.Views.LookEditPopup();

    // Router
    App.Routers.LookEditor = Backbone.Router.extend({
        routes: {
            'look/editor/photo/': 'create_photo',
            'look/editor/collage/': 'create_collage',
            'look/editor/:look_slug/': 'look_editor'
        },

        create_photo: function() {
            console.log('photo');
        },

        create_collage: function() {
            console.log('collage');
        },

        look_editor: function(look_slug) {
            console.log('look editor route', look_slug);
        }
    });

    // Initialize
    window.look_editor_router = new App.Routers.LookEditor();
    Backbone.history.start({pushState: true});
});
