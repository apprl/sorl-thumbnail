App.Views.FilterProductColor = Backbone.View.extend({

    events: {
        'click > a': 'open',
        'click li': 'select'
    },

    initialize: function(options) {
        this.collection.on('reset', this.render, this);
        this.sub_open = false;

        this.model.on('change:color', this.reset, this);

        $(document).on('click', _.bind(this.close, this));
    },

    reset: function(model, value, options) {
        if(!value || value == 0) {
            this.$el.find('span').text(this.$el.find('a').data('default-name'));
        }
    },

    select: function(e) {
        var color_id = $(e.target).addClass('selected').data('id');
        var color = this.collection.get(color_id);

        App.Events.trigger('product:facet', {type: 'color', value: color_id});

        if(!color) {
            this.$el.find('span').text(this.$el.find('a').data('default-name'));
        } else {
            this.$el.find('span').text(color.get('name'));
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

    close: function(e) {
        var $target = $(e.target);
        var $ptarget = $target.parent();
        var $pptarget = $ptarget.parent();

        if(!$target.is(this.$el) && !$ptarget.is(this.$el) && !$pptarget.is(this.$el)) {
            this.$el.removeClass('open').find('.glyphicon').addClass('glyphicon-chevron-down').removeClass('glyphicon-chevron-up');
            this.sub_open = false;
        }
    },

    make_element: function(id, name, count) {
        if(id <= 0) {
            var class_name = 'no-color'
        } else {
            var class_name = name;
        }
        var attrs = {'data-id': id, href: '#', 'class': class_name};
        var text = (count) ? name + ' (' + count + ')' : name;
        var text_element = $(this.make('a', attrs, text));

        if(count <= 0) {
            text_element.addClass('filtered')
        }

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
