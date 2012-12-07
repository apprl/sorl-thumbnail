App.Views.LookComponentCollage = App.Views.LookComponent.extend({

    className: 'product',

    template: _.template($('#look_component_collage').html()),

    render: function() {
        this.$el.css({left: this.model.get('left'),
                      top: this.model.get('top'),
                      width: this.model.get('width'),
                      height: this.model.get('height'),
                      'z-index': this.model.get('z_index'),
                      position: 'absolute'});

        this.$el.html(this.template(this.model.toJSON()));

        var container = $('#collage');

        this.$el.resizable({
            containment: container,
            aspectRatio: true,
            autoHide: false,
            maxHeight: container.height(),
            maxWidth: container.width(),
            minHeight: 50,
            minWidth: 50,
            stop: _.bind(function(event, ui) {
                this.model.set({width: ui.size.width, height: ui.size.height}, {silent: true});
            }, this)
        });

        this.$el.draggable({
            stack: '.product',
            containment: $('.look-container'),
            stop: _.bind(function(event, ui) {
                this.model.set({left: ui.position.left, top: ui.position.top}, {silent: true});
            }, this)
        });

        // TODO: rotatable does not work
        //this.$el.rotatable({
            //handles: 'ne',
            //autoHide: false,
            //stop: function(event, ui) {
                //console.log('save shit to model', ui.element, ui.rotation);
            //}
        //});

        return this;
    }

});
