App.Views.LookEditFilterTabs = Backbone.View.extend({

    el: '#product-tabs',

    events: {
        'click a': 'filter'
    },

    filter: function(e) {
        var $target = $(e.currentTarget);
        var user = $target.data('user');
        if ($target.hasClass('tab-likes') && user) {
            this.model.set('user_id', user);
        } else {
            this.model.unset('user_id');
        }

        $target.parent().siblings().find('a').removeClass('selected');
        $target.addClass('selected');
    }

});
