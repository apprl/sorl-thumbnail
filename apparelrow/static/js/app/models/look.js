window.App.Models.Look = Backbone.Model.extend({

    urlRoot: '/look/',

    localStorage: new Store('edit_look'),

    defaults: {
        'components': [],
        'published': false,
        'component': (external_look_type == 'photo') ? 'P' : 'C',
        'description': '',
        'title': '',
        'id': external_look_type
    },

    initialize: function() {
        if(external_look_id > 0) {
            this.backend = 'server';
            this.set('id', external_look_id, {silent: true});
        } else {
            this.backend = 'client';
            this.set('id', external_look_type, {silent: true});
        }
    },

    sync: function(method, model, options) {
        if(this.backend == 'client') {
            var resp;
            var store = model.localStorage || model.collection.localStorage;

            //model.id = model.attributes.id = external_look_type;

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
