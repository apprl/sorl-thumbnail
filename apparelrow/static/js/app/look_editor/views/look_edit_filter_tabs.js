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

    add_tab: function(parent, id, title, icon, view) {
        this.$el.append('<li><a class="tab-'+id+'" href="#"><img src="'+static_path+icon+'" width="16" height="16"></img> <span>'+title+'</span></a></li>');
        view.render().$el.appendTo(parent.$el).hide();
    },

    filter: function(e) {
        var $target = $(e.currentTarget);
        if (!$target.hasClass('active')) {
            $target.parent().siblings().removeClass('active');
            $target.parent().addClass('active');
            $('.product-chooser-wrapper').hide();
        }
        if ($target.hasClass('tab-likes') || $target.hasClass('tab-all')) {
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
            }

            $('#product-wrapper').show();
        } else {

            $('#'+$target[0].className.substr(4)+'-wrapper').show();
        }


        e.preventDefault();
    }

});
