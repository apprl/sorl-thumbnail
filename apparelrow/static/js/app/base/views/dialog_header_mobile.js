App.Views.DialogHeaderMobile = App.Views.Header.extend({

    events: {
        'click .btn': 'hide'
    },
    initialize: function(options) {
        _.extend(this.events, App.Views.Header.prototype.events);
        App.Views.DialogHeaderMobile.__super__.initialize(options);
    },

    hide: function() {
        App.Events.trigger('popup_dispatcher:hide');
    },

    render: function() {
        App.Views.Header.prototype.render.call(this);
        this.$el.children().removeClass('visible-md visible-lg');
        return this;
    }
});