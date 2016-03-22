App.Views.FilterProductStore = Backbone.View.extend({

    events: {
        'click > a': 'open',
        'click li': 'select'
    },

    initialize: function(options) {
        this.collection.on('reset', this.render, this);
        this.sub_open = false;

        this.model.on('change:store', this.reset, this);

        $(document).on('click', _.bind(this.close, this));
    },

    reset: function(model, value, options) {
        if(!value || value == 0) {
            App.Events.trigger('product:store_selected', 0);
            this.$el.find('span').text(this.$el.find('a').data('default-name'));
        }
    },

    select: function(e) {
        var store_id = $(e.target).addClass('selected').data('id');
        var store = this.collection.get(store_id);

        App.Events.trigger('product:facet', {type: 'store', value: store_id});

        if(!store) {
            App.Events.trigger('product:store_selected', 0);
            this.$el.find('span').text(this.$el.find('a').data('default-name'));
        } else {
            App.Events.trigger('product:store_selected', store_id);
            this.$el.find('span').text(store.get('name'));
        }

        e.preventDefault();
    },

    open: function(e) {
        if(this.sub_open) {
            this.$el.removeClass('open').find('.glyphicon').removeClass('glyphicon-chevron-up').addClass('glyphicon-chevron-down');
        } else {
            this.$el.addClass('open').find('.glyphicon').addClass('glyphicon-chevron-up').removeClass('glyphicon-chevron-down');
        }
        this.sub_open = !this.sub_open;

        e.preventDefault();
    },

    close: function(e) {
        var $target = $(e.target);
        var $ptarget = $target.parent();
        var $pptarget = $ptarget.parent();

        if(!$target.is(this.$el) && !$ptarget.is(this.$el) && !$pptarget.is(this.$el)) {
            this.$el.removeClass('open').find('.glyphicon').addClass('glyphicon-chevron-down').removeClass('glyphicon-chevron-up');
            this.sub_open = false;
        }
    },

    make_element: function(id, name) {
        var attrs = {'data-id': id, href: '#'};
        var text = name;
        var text_element = $(this.make('a', attrs, text));

        return $(this.make('li', {'data-id': id})).append(text_element);
    },

    update_height: function(height) {
        this.$el.find('ul').css('max-height', height);
    },

    render: function() {
        this.$el.find('ul').remove();
        var $ul = $(this.make('ul')).addClass('dropdown-menu');
        $ul.append(this.make_element(0, $('#product-chooser').data('reset-text')));
        this.collection.each(_.bind(function(model) {
            $ul.append(this.make_element(model.get('id'), model.get('name')))
        }, this));
        this.$el.append($ul);

        return this;
    }

});