App.Views.PopupDispatcher =  Backbone.View.extend({

    id: 'popup-slim',
    template: _.template($('#popup_slim_template').html()),

    events: {
        'click .close': 'hide'
    },

    content: {},

    initialize: function() {
        this.active = false;

        // Hide popup on ESC keydown and click
        $(document).on('keydown', _.bind(function(e) { if(this.active && e.keyCode == 27) { this.hide() } }, this));
        $(document).on('click', '.look-overlay-bg', _.bind(function(e) {
            if(this.active) {
                this.hide();
            }
        }, this));

        // Hide popup on global event
        App.Events.on('popup_dispatcher:hide', this.hide, this);

        this.$el.html(this.template());
        this.$overlay = $(this.make('div')).addClass('look-overlay-bg').css({position: 'absolute', top: 0, left: 0, width: '100%', height: $(document).height(), backgroundColor: '#000', opacity: 0.3, display: 'none', zIndex: 10089});
        $('body').append(this.$el, this.$overlay);
    },

    add: function(name, popup_class) {
        this.content[name] = popup_class;
    },

    remove: function(name) {
        delete this.content[name];
    },

    show: function(name, hide_animation) {
        var dialog = this.content[name];

        this.$el.find('.title').text(dialog.title);
        this.$el.find('.content').html(dialog.render(name).el);
        this.$el.removeClass().addClass('popup-slim-'+name);

        // TODO: ugly solution no/yes?
        dialog.delegateEvents();
        //this._center();
        this.$overlay.css('height', $(document).height());
        if(hide_animation) {
            this.$overlay.show();
            this.$el.show();
        } else {
            this.$overlay.fadeIn(200);
            this.$el.fadeIn(200);
        }

        // Listen to window resize for repositioning
        //$(window).on('resize.dialog', _.bind(this._center, this));

        this.active = name;
    },

    hide: function(hide_animation) {
        if (this.active && this.content.hasOwnProperty(this.active)) {
            var dialog = this.content[this.active];

            if (dialog.hasOwnProperty('hide')) {
                dialog.hide();
            }

            if (hide_animation) {
                this.$overlay.hide();
                this.$el.hide();
            } else {
                this.$overlay.fadeOut(200);
                this.$el.fadeOut(200);
            }
            this.active = false;

            // Remove listener
            $(window).off('resize.dialog');
        }
        return false;
    },

    _center: function(){
        var width = this.$el.width();
        var height = this.$el.height();
        var window_width = $(window).width();
        var window_height = $(window).height();

        this.$el.css({
            'left': (window_width / 2) - (width / 2),
            'top': (window_height / 2) - (height / 2)
        });

        this.$overlay.css('height', $(document).height());
    }

});
