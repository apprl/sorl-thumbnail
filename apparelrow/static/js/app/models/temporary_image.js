window.App.Models.TemporaryImage = Backbone.Model.extend({

    localStorage: new Store('temporary-image'),

    parse: function(response) {
        return response[0];
    },

    sync: function(method, model, options) {
        var resp;
        var store = model.localStorage || model.collection.localStorage;

        switch (method) {
            case 'read':
                resp = model.id ? store.find(model) : store.findAll();
                break;
            case 'create':
                resp = store.create(model);
                break;
            case 'update':
                resp = store.update(model);
                break;
            case 'delete':
                resp = store.destroy(model);
                break;
        }

        if (resp) {
            options.success(resp);
        } else {
            options.error('Record not found');
        }
    }

});
