/**
 * Created by deploy on 10/17/14.
 */

var ApprlEmbed = ApprlEmbed || function(p, id, n, w, h, o) {
	var self = this;
	var host = 'http://'+window.location.host;

	self.container = document.createElement('div');
	self.frame = document.createElement('iframe');
	self.frame.setAttribute('src', '//'+ o +'/embed/look/'+id+'/'+n+'/?host='+ encodeURIComponent(host));
	self.frame.setAttribute('width', w);
	self.frame.setAttribute('height', h);
	self.container.appendChild(self.frame);
	p.parentNode.insertBefore(self.container, p);

	this.setRatio = function() {
		self.ratio = self.frame.offsetHeight / self.frame.offsetWidth;
	};

	this.onResize = function() {
		self.frame.height = self.frame.offsetWidth * self.ratio + 'px';
	};

    this.setHeight = function(height) {
      self.frame.setAttribute('height', height);
      self.setRatio();
    };

	self.setRatio();

	window.addEventListener('resize', self.onResize);
    window.addEventListener('message', function(e) {
        if(e.origin == 'http://' + o) {
            self.setHeight(e.data);
        }
    });
};