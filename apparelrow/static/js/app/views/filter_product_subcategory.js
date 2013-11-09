App.Views.FilterProductSubCategory = Backbone.View.extend({

    events: {
        'click > a': 'open',
        'click li': 'select'
    },

    initialize: function(options) {
        this.parent_category_id == 0;
        this.sub_open = false;
        this.collection.on('reset', this.render, this);

        App.Events.on('product:category_selected', this.update, this);

        $(document).on('click', _.bind(this.close, this));
    },

    update: function(category_id) {
        this.parent_category_id = category_id;
        this.$el.find('span').text(this.$el.find('a').data('default-name'));
        App.Events.trigger('product:facet', {type: 'category', value: this.parent_category_id});
    },

    select: function(e) {
        var category_id = $(e.target).addClass('selected').data('id');
        var category = this.collection.get(category_id);

        if(!category) {
            this.$el.find('span').text(this.$el.find('a').data('default-name'));
            App.Events.trigger('product:facet', {type: 'category', value: this.parent_category_id});
        } else {
            this.$el.find('span').text(category.get('name'));
            App.Events.trigger('product:facet', {type: 'category', value: category_id});
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
        var text = (count) ? name + ' (' + count + ')' : name;

        return $(this.make('li', {'data-id': id})).append(this.make('a', attrs, text));
    },

    update_height: function(height) {
        this.$el.find('ul').css('max-height', height);
    },

    render: function() {
        if(this.parent_category_id > 0) {
            var subcategories = this.collection.where({parent: this.parent_category_id});
            if(subcategories.length > 0) {
                this.$el.find('ul').remove();
                var $ul = $(this.make('ul')).addClass('dropdown-menu');
                $ul.append(this.make_element(0, $('#product-chooser').data('reset-text')));
                _.each(subcategories, _.bind(function(model) {
                    $ul.append(this.make_element(model.get('id'), model.get('name')));

                    var subsubcategories = this.collection.where({parent: model.get('id')});
                    _.each(subsubcategories, _.bind(function(model) {
                        $ul.append(this.make_element(model.get('id'), '&nbsp;&nbsp;' + model.get('name')));
                    }, this));

                }, this));
                this.$el.append($ul);
                this.$el.show();
            } else {
                App.Events.trigger('product:facet', {type: 'category', value: this.parent_category_id});
                this.$el.find('span').text(this.$el.find('a').data('default-name'));
                this.$el.hide();
            }
        } else {
            this.$el.find('span').text(this.$el.find('a').data('default-name'));
            this.$el.hide();
        }

        return this;
    }

});
