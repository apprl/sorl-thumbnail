App.Views.PopupDispatcher = Backbone.View.extend({

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
        $(document).on('click', _.bind(function(e) {
            if(this.active && $(e.target).closest('#popup-slim').length == 0) {
                this.hide();
            }
        }, this));

        // Hide popup on global event
        App.Events.on('popup_dispatcher:hide', this.hide, this);

        this.$el.html(this.template());
        $('body').append(this.$el);
    },

    add: function(name, popup_class) {
        this.content[name] = popup_class;
    },

    remove: function(name) {
        delete this.content[name];
    },

    show: function(name) {
        var dialog = this.content[name];

        this.$el.find('.title').text(dialog.title);
        this.$el.find('.content').html(dialog.render().el);
        // TODO: ugly solution no/yes?
        dialog.delegateEvents();
        this._center();
        this.$el.show();

        this.active = name;
    },

    hide: function() {
        var dialog = this.content[this.active];

        if(dialog.hasOwnProperty('hide')) {
            dialog.hide();
        }
        this.$el.hide();
        this.active = false;

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
    }

});
