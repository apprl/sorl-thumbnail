/*
 * jQuery UI Rotatable 0.7.0
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

$.widget("ui.rotatable", $.ui.mouse, {
	widgetEventPrefix: "rotate",
	options: {
		handles: "nw",
        autoHide: false,
		zIndex: 1000,
		reRotate: /rotate\((-?\d+)deg\)/,
		cssRules: ['transform', 'WebkitTransform', 'MozTransform']
	},
    _get_rotation: function(style) {
        for(var i = 0; i < this.options.cssRules.length; i++) {
            var p = this.options.cssRules[i];
            if(typeof style[p] != 'undefined') {
                r = style[p].match(this.options.reRotate);
                return r && r[1] ? parseInt(r[1]) : 0;
            }
        }
        return 0;
    },
    _swap_rotation: function(from, to) {
        to.css({
            'transform': 'rotate(' + this.rotation + 'deg)',
            '-moz-transform': 'rotate(' + this.rotation + 'deg)',
            '-webkit-transform': 'rotate(' + this.rotation + 'deg)'
        });
        
        for(var i = 0; i < this.options.cssRules.length; i++) {
            var rule      = this.options.cssRules[i];
            var transform = from.get(0).style[rule];
            
            if(typeof transform != 'undefined') {
                from.get(0).style[rule] = transform.replace(this.options.reRotate, '');
                break;
            }
        }
    },
	_create: function() {
        var self = this, o = this.options;
        if(!($.browser.mozilla || $.browser.webkit))
            return;
		this.element.addClass("ui-rotatable");
		this.rotatedElement = this.element.is('.ui-wrapper') ? this.element.children().first() : this.element;
        this.rotation = this._get_rotation(this.rotatedElement.get(0).style);

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
				"rotatable", this.element.data('rotatable')
			);
			this.elementIsWrapper = true;
            
            // Let wrapper take over rotation from original element
            this._swap_rotation(this.originalElement, this.element);
		} else if(this.element != this.rotatedElement) {
		    // If element is already rotated, take it's rotation property
            this._swap_rotation(this.rotatedElement, this.element);
		}

		this.handles = o.handles || (!$('.ui-rotatable-handle', this.element).length ? "nw" : { se: '.ui-rotatable-se', sw: '.ui-rotatable-sw', ne: '.ui-rotatable-ne', nw: '.ui-rotatable-nw' });
		if(this.handles.constructor == String) {

			if(this.handles == 'all') this.handles = 'se,sw,ne,nw';
			var n = this.handles.split(","); this.handles = {};

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
				.addClass("ui-rotatable-autohide")
				.hover(function() {
					$(this).removeClass("ui-rotatable-autohide");
					self._handles.show();
				},
				function(){
					if (!self.rotating) {
						$(this).addClass("ui-rotatable-autohide");
						self._handles.hide();
					}
				});
		}

		//Initialize the mouse interaction
		this._mouseInit();

	},

	destroy: function() {

		this._mouseDestroy();

		var _destroy = function(exp) {
			$(exp).removeClass("ui-rotatable ui-rotatable-disabled ui-rotatable-rotating")
				.removeData("rotatable").unbind(".rotatable").find('.ui-rotatable-handle').remove();
		};

		//TODO: Unwrap at same DOM position
		if (this.elementIsWrapper) {
			_destroy(this.element);
			var wrapper = this.element;
			wrapper.after(
				this.originalElement.css({
					position: wrapper.css('position'),
					width: wrapper.outerWidth(),
					height: wrapper.outerHeight(),
					top: wrapper.css('top'),
					left: wrapper.css('left'),
                    'transform': 'rotate(' + this.rotation + 'deg)',
                    '-moz-transform': 'rotate(' + this.rotation + 'deg)',
                    '-webkit-transform': 'rotate(' + this.rotation + 'deg)'
                })
			).remove();
		}

		_destroy(this.originalElement);

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

	_mouseStart: function(event) {

        var el = this.element;
		this.rotating = true;

		// bugfix for http://dev.jquery.com/ticket/1749
		//if (el.is('.ui-draggable') || (/absolute/).test(el.css('position'))) {
			//el.css({ position: 'absolute', top: iniPos.top, left: iniPos.left });
		//}

		//Opera fixing relative position
		if ($.browser.opera && (/relative/).test(el.css('position')))
			el.css({ position: 'relative', top: 'auto', left: 'auto' });

		this.originalMousePosition = { left: event.pageX, top: event.pageY };
        this.originalRotation = this.rotation;

	    var cursor = $('.ui-rotatable-' + this.axis).css('cursor');
	    $('body').css('cursor', cursor == 'auto' ? this.axis + '-rotate' : cursor);

		el.addClass("ui-rotatable-rotating");
		this._propagate("start", event);
		return true;
	},

	_mouseDrag: function(event) {

		//Increase performance, avoid regex
		var el = this.element, self = this, smp = this.originalMousePosition, a = this.axis;

        // Midpoint of element
        var xm = el.offset().left + el.width() / 2;
        var ym = el.offset().top + el.height() / 2;
        // Delta between midpoint and original position
        var dx0 = smp.left - xm, dy0 = smp.top - ym;
        // Delta between midpoint and current position
        var dx1 = event.pageX - xm, dy1 = event.pageY - ym;
        // Delta between original position and current
		var dx = (event.pageX-smp.left)||0, dy = (event.pageY-smp.top)||0;
		var trigger = this._change[a];
		if (!trigger) return false;

		// Calculate the attrs that will be change
		var data = trigger.apply(this, [event, dx, dy, dx0, dy0, dx1, dy1]);

		// plugins callbacks need to be called first
		this._propagate("rotate", event);

        this._updateCache(data);

		el.css({
            'transform': 'rotate(' + self.rotation + 'deg)',
            '-moz-transform': 'rotate(' + self.rotation + 'deg)',
            '-webkit-transform': 'rotate(' + self.rotation + 'deg)'
		});

		// calling the user callback at the end
		this._trigger('rotate', event, this.ui());

		return false;
	},

	_mouseStop: function(event) {

		this.rotating = false;

		$('body').css('cursor', 'auto');

		this.element.removeClass("ui-rotatable-rotating");

		this._propagate("stop", event);

		return false;

	},

	_change: {
		se: function(event, dx, dy, dx0, dy0, dx1, dy1) {
			return this._change.nw.apply(this, [event, dx, dy, dx0, dy0, dx1, dy1]);
		},
		sw: function(event, dx, dy, dx0, dy0, dx1, dy1) {
			return this._change.nw.apply(this, [event, dx, dy, dx0, dy0, dx1, dy1]);
		},
		ne: function(event, dx, dy, dx0, dy0, dx1, dy1) {
			return this._change.nw.apply(this, [event, dx, dy, dx0, dy0, dx1, dy1]);
		},
		nw: function(event, dx, dy, dx0, dy0, dx1, dy1) {
            var a2 = dx * dx + dy * dy
              , b2 = dx0 * dx0 + dy0 * dy0
              , c2 = dx1 * dx1 + dy1 * dy1;
            // Cosine law
            var cos_a = (b2 + c2 - a2)/(2 * Math.sqrt(b2) * Math.sqrt(c2));
            // Arccos and convert to degrees
            var angle = Math.round(Math.acos(cos_a) * 180 / Math.PI);
            var sign = dx < 0 || dy < 0 ? -1 : 1;
            return sign * angle;
		}
	},

    _updateCache: function(rotation) {
        this.rotation = this.originalRotation + rotation;
    },

	_propagate: function(n, event) {
		$.ui.plugin.call(this, n, [event, this.ui()]);
		(n != "rotate" && this._trigger(n, event, this.ui()));
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
	version: "0.8.0"
});

var num = function(v) {
	return parseInt(v, 10) || 0;
};

var isNumber = function(value) {
	return !isNaN(parseInt(value, 10));
};

})(jQuery);
