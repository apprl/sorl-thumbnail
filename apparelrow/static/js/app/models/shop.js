window.App.Models.Shop = window.App.Models.WidgetModelBase.extend({
    urlRoot: create_store_api_base_url,
    localStorage: new Store('create_store'),

    defaults: {
        'published': false,
        'title': '',
        'description': '',
        'id': 50
    },

    initialize: function() {
        console.log("ShopModel init");
    }
});