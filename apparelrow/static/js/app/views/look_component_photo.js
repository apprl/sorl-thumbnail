App.Views.LookComponentPhoto = App.Views.LookComponent.extend({

    className: 'hotspot',

    template: _.template($('#look_component_photo').html()),

    render: function() {
        this.$el.css({left: this.model.get('left'),
                      top: this.model.get('top'),
                      width: this.model.get('width'),
                      height: this.model.get('height'),
                      'z-index': this.model.get('z_index'),
                      position: 'absolute'});

        this.$el.html(this.template(this.model.toJSON()));

        this.$el.draggable({
            stack: '.hotspot',
            containment: $('.look-container'),
            stop: _.bind(function(event, ui) {
                this.model.set({left: ui.position.left, top: ui.position.top}, {silent: true});
                App.Events.trigger('look:dirty');
            }, this)
        });

        return this;
    }

});
