/**
 * Created by deploy on 10/17/14.
 */

var ApprlEmbed = ApprlEmbed || function(p, id, n, w, h, o, t) {
	var self = this;
	var host = 'http://'+window.location.host;
    var iframeSrc;

    if(t == 'look') {
        iframeSrc = '//'+ o +'/embed/'+ t +'/'+id+'/'+n+'/?host='+ encodeURIComponent(host);
    } else if(t == 'shop') {
        iframeSrc = '//'+ o +'/embed/'+ t +'/'+id+'/?host='+ encodeURIComponent(host)
    }
	self.container = document.createElement('div');
    self.container.setAttribute('style', 'width: ' + w + ';margin: 0 auto;');
	self.frame = document.createElement('iframe');
	self.frame.setAttribute('src', iframeSrc);
	self.frame.setAttribute('width', w);
    self.frame.setAttribute('scrolling', t == 'shop' ? 'yes' : 'no');
	self.frame.setAttribute('height', h);
    self.frame.setAttribute('frameborder', 0);
	self.container.appendChild(self.frame);
	p.parentNode.insertBefore(self.container, p);

	this.setRatio = function() {
		self.ratio = self.frame.offsetHeight / self.frame.offsetWidth;
	};

	this.onResize = function() {
		self.frame.height = self.frame.offsetWidth * self.ratio + 'px';
	};

    this.setHeight = function(height) {
      var values = height.split('|');
      if(id == values[1]) {
          self.frame.setAttribute('height', values[0]);
          self.setRatio();
      }
    };

	self.setRatio();

	window.addEventListener('resize', self.onResize);
    window.addEventListener('message', function(e) {
        if(e.origin == 'http://' + o) {
            self.setHeight(e.data);
        }
    });
};