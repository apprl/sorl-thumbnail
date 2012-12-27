jQuery(document).ready(function() {
    window.search_product = new App.Models.SearchProduct();
    window.products = new App.Collections.Products();
    window.facet_container = new App.Models.FacetContainer();
    window.filter_product = new App.Views.FilterProduct({search_product: search_product,
                                                         products: products,
                                                         facet_container: facet_container});
    window.product_list = new App.Views.Products({collection: products});

    // Look edit view
    window.look = new App.Models.Look();
    window.look_edit_title = new App.Views.LookEditTitle({model: look});
    window.look_edit_description = new App.Views.LookEditDescription({model: look});
    window.look_edit = new App.Views.LookEdit({model: look});

    // Router
    App.Routers.LookEditor = Backbone.Router.extend({
        routes: {
            'look/editor/photo/': 'editor_photo',
            'look/editor/collage/': 'editor_collage'
        },

        editor_photo: function() {
            console.log('photo');
        },

        editor_collage: function() {
            console.log('collage');
        }
    });

    // Initialize
    window.look_editor_router = new App.Routers.LookEditor();
    Backbone.history.start({pushState: true});
});
