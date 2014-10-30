App.Views.FilterProductPrice = Backbone.View.extend({

    events: {
        'click > a': 'open',
        'click li': 'select'
    },

    initialize: function(options) {
        this.collection.on('reset', this.render, this);
        this.sub_open = false;

        this.model.on('change:price', this.reset, this);

        $(document).on('click', _.bind(this.close, this));
    },

    reset: function(model, value, options) {
        if(!value || value == 0) {
            this.$el.find('span').text(this.$el.find('a').data('default-name'));
        }
    },

    select: function(e) {
        var category_id = $(e.target).addClass('selected').data('id');
        var category = this.collection.get(category_id);

        App.Events.trigger('product:facet', {type: 'price', value: category_id});

        if(!category) {
            this.$el.find('span').text(this.$el.find('a').data('default-name'));
        } else {
            this.$el.find('span').text(category.get('name'));
        }

        e.preventDefault();
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
        var $target = $(e.target);
        var $ptarget = $target.parent();
        var $pptarget = $ptarget.parent();

        if(!$target.is(this.$el) && !$ptarget.is(this.$el) && !$pptarget.is(this.$el)) {
            this.$el.removeClass('open');
            this.sub_open = false;
        }
    },

    make_element: function(id, name, count) {
        var attrs = {'data-id': id, href: '#'};
        var text_element = $(this.make('a', attrs, name));

        return $(this.make('li', {'data-id': id})).append(text_element);
    },

    render: function() {
        this.$el.find('ul').remove();
        var $ul = $(this.make('ul')).addClass('dropdown-menu');
        $ul.append(this.make_element(0, $('#product-chooser').data('reset-text')));
        this.collection.each(_.bind(function(model) {
            $ul.append(this.make_element(model.get('id'), model.get('name'), model.get('count')))
        }, this));
        this.$el.append($ul);

        return this;
    }

});
