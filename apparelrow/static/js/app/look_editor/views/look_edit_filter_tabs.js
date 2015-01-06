App.Views.LookEditFilterTabs = Backbone.View.extend({

    el: '#product-tabs',

    events: {
        'click a': 'filter'
    },

    initialize: function() {
        var $tab_likes = this.$el.find('.tab-likes');
        if($tab_likes.parent().hasClass('active')) {
            this.model.set('user_id', $tab_likes.data('user'), {silent: true});
        }
    },

    filter: function(e) {
        var $target = $(e.currentTarget);
        if (!$target.hasClass('active')) {
            var user = $target.data('user');
            if ($target.hasClass('tab-likes') && user) {
                this.model.set('user_id', user);
            } else if ($target.hasClass('tab-likes') && !isAuthenticated) {
                App.Events.trigger('product_list:unauthenticated', true);
            } else {
                App.Events.trigger('product_list:unauthenticated', false);
                this.model.unset('user_id');
            }

            $target.parent().siblings().removeClass('active');
            //$target.parent().siblings().find('a').removeClass('selected');
            $target.parent().addClass('active');
        }
        e.preventDefault();
    }

});
