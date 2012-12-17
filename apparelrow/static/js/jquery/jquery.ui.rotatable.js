/*
 * jQuery UI Rotatable 0.9.0
 *
 * Copyright (c) 2010 Linus G Thiel (Hansson & Larsson)
 * Dual licensed under the MIT (MIT-LICENSE.txt)
 * and GPL (GPL-LICENSE.txt) licenses.
 *
 * Depends:
 *	jquery.ui.core.js
 *	jquery.ui.mouse.js
 *	jquery.ui.widget.js
 */
(function($) {

$.widget('ui.rotatable', $.ui.mouse, {

	widgetEventPrefix: 'rotate',

	options: {
		handles: 'nw',
        autoHide: false,
		zIndex: 100000,
		reRotate: /rotate\((-?\d+)deg\)/,
		cssRules: ['transform', 'WebkitTransform', 'MozTransform']
	},

    _get_rotation: function(element) {
        var transform = element.css('transform');

        if(transform && transform !== 'none') {
            if(transform.indexOf('rotate') == 0) {
                var r = transform.match(this.options.reRotate);
                return r && r[1] ? parseInt(r[1]) : 0;
            } else if(transform.indexOf('transform') == 0) {
                var values = transform.split('(')[1].split(')')[0].split(',');
                var a = values[0];
                var b = values[1];
                return Math.round(Math.atan2(b, a) * (180/Math.PI));
            }
        }

        return 0;
    },

    _swap_rotation: function(from, to) {
        to.css('transform', 'rotate(' + this.rotation + 'deg)');
        from.css('transform', 'rotate(0deg)');
    },

    // TODO: understand this method, probably should use rotatedElement instead of element?
	_create: function() {
        var self = this, o = this.options;

        // XXX: should work for every browser, if not use modernizr
        //if(!($.browser.mozilla || $.browser.webkit))
            //return;

		this.element.addClass('ui-rotatable');
		this.rotatedElement = this.element.is('.ui-wrapper') ? this.element.children().first() : this.element;
        this.rotation = this._get_rotation(this.rotatedElement);

		$.extend(this, {
			originalElement: this.element
		});

		//Wrap the element if it cannot hold child nodes
		if(this.element[0].nodeName.match(/canvas|textarea|input|select|button|img/i)) {

			//Opera fix for relative positioning
			if (/relative/.test(this.element.css('position')) && $.browser.opera)
				this.element.css({ position: 'relative', top: 'auto', left: 'auto' });

			//Create a wrapper element and set the wrapper to the new current internal element
			this.element.wrap(
				$('<div class="ui-wrapper" style="overflow: hidden;"></div>').css({
					position: this.element.css('position'),
					width: this.element.outerWidth(),
					height: this.element.outerHeight(),
					top: this.element.css('top'),
					left: this.element.css('left')
				})
			);

			//Overwrite the original this.element
			this.element = this.element.parent().data(
				'rotatable', this.element.data('rotatable')
			);
			this.elementIsWrapper = true;

            // Let wrapper take over rotation from original element
            this._swap_rotation(this.originalElement, this.element);
		} else if(this.element != this.rotatedElement) {
		    // If element is already rotated, take it's rotation property
            this._swap_rotation(this.rotatedElement, this.element);
		}

		this.handles = o.handles || (!$('.ui-rotatable-handle', this.element).length ? 'nw' : { se: '.ui-rotatable-se', sw: '.ui-rotatable-sw', ne: '.ui-rotatable-ne', nw: '.ui-rotatable-nw' });
		if(this.handles.constructor == String) {

			if(this.handles == 'all') this.handles = 'se,sw,ne,nw';
			var n = this.handles.split(','); this.handles = {};

			for(var i = 0; i < n.length; i++) {

				var handle = $.trim(n[i]), hname = 'ui-rotatable-'+handle;
				var axis = $('<div class="ui-rotatable-handle ' + hname + '"></div>');

				// increase zIndex of sw, se, ne, nw axis
				//TODO : this modifies original option
				if(/sw|se|ne|nw/.test(handle)) axis.css({ zIndex: ++o.zIndex });

                axis.addClass('ui-icon');

				//Insert into internal handles object and append to element
				this.handles[handle] = '.ui-rotatable-'+handle;
				this.element.append(axis);
			}

		}

		this._handles = $('.ui-rotatable-handle', this.element)
			.disableSelection();

		//Matching axis name
		this._handles.mouseover(function() {
			if (!self.rotating) {
				if (this.className)
					var axis = this.className.match(/ui-rotatable-(se|sw|ne|nw)/i);
				//Axis, default = se
				self.axis = axis && axis[1] ? axis[1] : 'nw';
			}
		});

		//If we want to auto hide the elements
		if (o.autoHide) {
			this._handles.hide();
			$(this.element)
				.addClass('ui-rotatable-autohide')
				.hover(function() {
					$(this).removeClass('ui-rotatable-autohide');
					self._handles.show();
				},
				function(){
					if (!self.rotating) {
						$(this).addClass('ui-rotatable-autohide');
						self._handles.hide();
					}
				});
		}

		// Initialize the mouse interaction
		this._mouseInit();
	},

    // In jQuery UI 1.9 and above, you would define _destroy instead of destroy
    // and not call the base method
	_destroy: function() {

        // Destroy the mouse interaction
		this._mouseDestroy();

		var destroyElement = function(exp) {
			$(exp).removeClass('ui-rotatable ui-rotatable-disabled ui-rotatable-rotating')
				.removeData('rotatable').unbind('.rotatable').find('.ui-rotatable-handle').remove();
		};

		//TODO: Unwrap at same DOM position
		if (this.elementIsWrapper) {
			destroyElement(this.element);
			var wrapper = this.element;
			wrapper.after(
				this.originalElement.css({
					position: wrapper.css('position'),
					width: wrapper.outerWidth(),
					height: wrapper.outerHeight(),
					top: wrapper.css('top'),
					left: wrapper.css('left'),
                    'transform': 'rotate(' + this.rotation + 'deg)'
                })
			).remove();
		}

		destroyElement(this.originalElement);

		return this;
	},

	_mouseCapture: function(event) {
		var handle = false;
		for (var i in this.handles) {
			if ($(this.handles[i], this.element)[0] == event.target) {
				handle = true;
			}
		}

		return !this.options.disabled && handle;
	},

    _getCenter: function(element) {
        element.css('transform','rotate(0deg)');

        var imageOffset = element.offset();
        var imageCentreX = imageOffset.left + element.width() / 2;
        var imageCentreY = imageOffset.top + element.height() / 2;

        element.css('transform','rotate(' + this.rotation + 'deg)');

        return {x: imageCentreX, y: imageCentreY};
    },

	_mouseStart: function(event) {
		this.rotating = true;

	    var cursor = $('.ui-rotatable-' + this.axis).css('cursor');
	    $('body').css('cursor', cursor == 'auto' ? this.axis + '-rotate' : cursor);

		this.element.addClass('ui-rotatable-rotating');
		this._propagate('start', event);

        var center = this._getCenter(this.element);
        this.mouseStartAngle = Math.atan2(event.pageY - center.y, event.pageX - center.x);
        this.originalRotation = this.rotation;

		return true;
	},

	_mouseDrag: function(event) {
		// plugins callbacks need to be called first
		this._propagate('rotate', event);

        var center = this._getCenter(this.element);
        var mouseAngle = Math.atan2(event.pageY - center.y, event.pageX - center.x);
        this.rotation = this._radToDeg(mouseAngle - this.mouseStartAngle) + this.originalRotation;

        this.element.css({'transform': 'rotate(' + this.rotation + 'deg)'});

		// calling the user callback at the end
		this._trigger('rotate', event, this.ui());

		return false;
	},

	_mouseStop: function(event) {
		this.rotating = false;
		this.element.removeClass('ui-rotatable-rotating');
		this._propagate('stop', event);

		$('body').css('cursor', 'auto');

		return false;

	},

	_propagate: function(n, event) {
		$.ui.plugin.call(this, n, [event, this.ui()]);
		(n != 'rotate' && this._trigger(n, event, this.ui()));
	},

    _degToRad: function(d) {
        return (d * (Math.PI / 180));
    },

    _radToDeg: function(r) {
        return (r * (180 / Math.PI));
    },

    plugins: {},

	ui: function() {
		return {
			originalElement: this.originalElement,
			element: this.element,
            rotation: this.rotation
		};
	}

});

$.extend($.ui.rotatable, {
	version: '0.9.0'
});

})(jQuery);
