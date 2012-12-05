App.Views.FilterProductCategory = Backbone.View.extend({

    events: {
        'click > a': 'open',
        'click li': 'select'
    },

    initialize: function(options) {
        this.collection.on('reset', this.render, this);
        this.sub_open = false;

        $(document).on('click', _.bind(this.close, this));
    },

    select: function(e) {
        var category_id = $(e.target).addClass('selected').data('id');
        App.Events.trigger('product:facet', {type: 'category', value: category_id});
    },

    open: function(e) {
        if(this.sub_open) {
            this.$el.removeClass('open');
        } else {
            this.$el.addClass('open');
        }
        this.sub_open = !this.sub_open;

        e.preventDefault();
    },

    close: function(e) {
        if(!$(e.target).is(this.$el) && !$(e.target).parent().is(this.$el)) {
            this.$el.removeClass('open');
            this.sub_open = false;
        }
    },

    render: function() {
        // TODO: how to handle selected, multiple selections?
        // TODO: template?
        this.$el.find('ul').remove();
        this.$el.append(this.make('ul'));
        this.collection.each(_.bind(function(model) {
            var a_attrs = {'data-id': model.get('id'), href: '#'};
            this.$el.find('ul').append(
                $(this.make('li', {'data-id': model.get('id')})).append(
                    this.make('a', a_attrs, model.get('name') + ' (' + model.get('count') + ')')
                )
            );
        }, this));

        return this;
    }

});
