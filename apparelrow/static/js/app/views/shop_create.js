App.Views.ShopCreate = App.Views.WidgetBase.extend({
    el: '#shop-preview',
    initialize: function() {
        App.Events.on('look_edit:product:add', this.pending_add_component, this);
    },
    pending_add_component: function(product) {
        console.log("Add product", product);
        //this.pending_product = product;
    }
});