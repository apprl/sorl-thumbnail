window.App.Models.ProductWidget = window.App.Models.WidgetModelBase.extend({
    urlRoot: create_product_widget_api_base_url,
    localStorage: new Store('create_product_widget'),

    defaults: {
        'published': false,
        'title': '',
        'description': '',
        'id': external_product_widget_id
    },

    initialize: function() {
        this._dirty = false;
        this.components = new App.Collections.ProductWidgetComponents();

        if(external_product_widget_id) {
            this.backend = 'server';
            this.set('id', external_product_widget_id, { silent: true });
        } else {
            this.backend = 'client';
            this.set('id', external_product_widget_id, { silent: true });
        }

        $(window).on('beforeunload', _.bind(function(e) {
            if(this._dirty) {
                return 'You have unsaved changes that will be deleted if you leave this page without saving.';
            }
        }, this));

        App.Events.on('product_widget:dirty', this.dirty, this);
        App.Events.on('widget:reset', this.reset, this);
    },

    dirty: function() {
        this._dirty = true;
    },

    reset: function() {
        this.clear({ silent: true });
        this.set(_.clone(this.defaults), { silent: true });
        this.components.reset([], { silent: true });
        this._dirty = false;
        this.backend = 'client';
        this.save();
    },

    parse: function(response) {
        if(response) {
            cloned_response = _.clone(response);

            if(!cloned_response.hasOwnProperty('components')) {
                cloned_response.components = [];
            }

            this.components.reset(cloned_response.components, { silent: true});
            delete cloned_response.components;

            return cloned_response;
        }
    },
    toJSON: function() {
        var json = _.clone(this.attributes);
        json.components = this.components.map(function(model) {
            return model.toJSON();
        });

        return json;
    },
    save: function(key, value, options) {
        Backbone.Model.prototype.save.call(this, key, value, options);
    },
    sync: function(method, model, options) {
        if(this.backend == 'client') {
            var resp;
            var product_widget = model.localStorage || model.collection.localStorage;

            switch(method) {
                case 'read':
                    resp = model.id ? product_widget.find(model) : product_widget.findAll();
                    break;
                case 'create':
                    resp = product_widget.create(model);
                    break;
                case 'update':
                    resp = product_widget.update(model);
                    break;
                case 'delete':
                    resp = product_widget.destroy(model);
                    break;
            }

            if(resp) {
                options.success(resp);
            } else {
                options.error("Record not found");
            }
        } else {
            return Backbone.sync.apply(this, arguments);
        }
    }
});