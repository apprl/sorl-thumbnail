App.Views.FilterProductCategory = Backbone.View.extend({

    tagName: 'select',

    events: {
        'change': 'update',
    },

    initialize: function(options) {
        this.collection.on('reset', this.render, this);
        this.render();
    },

    render: function() {
        var category_id = this.$el.find('option:selected').val();
        this.$el.empty();
        this.$el.append(this.make('option', {value: 0}, 'CATEGORY'));
        this.collection.each(_.bind(function(model) {
            var option_el = this.make('option', {value: model.get('id')}, model.get('name') + ' ' + model.get('count'));
            if(model.get('id') == category_id) {
                option_el.selected = 'selected';
            }
            this.$el.append(option_el);
        }, this));

        return this;
    },

    update: function() {
        var category_id = this.$el.find('option:selected').val();
        App.Events.trigger('product:facet', {type: 'category', value: category_id});
    }

});
