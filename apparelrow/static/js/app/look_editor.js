jQuery(document).ready(function() {
    // Product filter view
    window.filter_product_view = new App.Views.FilterProduct();

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

            filter_product_view.disable();
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
