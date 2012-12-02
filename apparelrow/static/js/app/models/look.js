window.App.Models.Look = Backbone.Model.extend({

    urlRoot: '/look/',

    localStorage: new Store('edit_look'),

    defaults: {
        'published': false,
        'component': (external_look_type == 'photo') ? 'P' : 'C',
        'description': '',
        'title': '',
        'id': external_look_type
    },

    initialize: function() {
        console.log('look initialize');

        this.components = new App.Collections.LookComponents();

        if(external_look_id > 0) {
            this.backend = 'server';
            this.set('id', external_look_id, {silent: true});
        } else {
            this.backend = 'client';
            this.set('id', external_look_type, {silent: true});
        }
    },

    parse: function(response) {
        cloned_response = _.clone(response);

        if(!cloned_response.hasOwnProperty('components')) {
            cloned_response.components = [];
        }
        this.components.reset(cloned_response.components, {silent: true});
        delete cloned_response.components;

        console.log('parse look', cloned_response, response);

        return cloned_response;
    },

    toJSON: function() {
        var json = _.clone(this.attributes);
        json.components = this.components.map(function(model) { return model.toJSON(); });

        console.log('look toJSON', json);

        return json;
    },

    sync: function(method, model, options) {
        console.log('look sync', method);
        if(this.backend == 'client') {
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
                options.error("Record not found");
            }
        } else {
            return Backbone.sync.apply(this, arguments);
        }
    }

});
