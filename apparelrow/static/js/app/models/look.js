window.App.Models.Look = Backbone.Model.extend({

    urlRoot: '/look',

    localStorage: new Store('edit_look'),

    defaults: {
        'components': []
    },

    initialize: function() {
        if(external_look_id > 0) {
            this.backend = 'server';
            this.id = this.attributes.id = external_look_id;
        } else {
            this.backend = 'client';
        }
    },

    sync: function(method, model, options) {
        if(this.backend == 'client') {
            var resp;
            var store = model.localStorage || model.collection.localStorage;

            // TODO: ugly solution to set id for when backend is client
            model.id = model.attributes.id = external_look_type;

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
                options.error("Record not found");
            }
        } else {
            return Backbone.sync.apply(this, arguments);
        }
    }

});
