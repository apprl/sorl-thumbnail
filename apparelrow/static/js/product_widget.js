function inViewport(node) {
    var rect = node.getBoundingClientRect();
    var html = document.documentElement;
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || html.clientHeight) &&
        rect.right <= (window.innerWidth || html.clientWidth)
    );
}

function loadImgs(imgs) {
    return imgs.map(function(i) {
        var node = $(this);
        if(inViewport(node[0])) {
            node.attr('src', node.data().src)
            node.removeAttr('data-src')
            return null
        } else {
            return node
        }
    })

}

jQuery(document).ready(function() {
    var $ul = $('ul.productcontainer');
    var $items = $ul.children('li.product');
    var index = 0;
    var running = false;
    var visiblechildren;
    var doslide = false;
    var $container = $('.slidecontainer');
    var padding = 20;
    var $slidenext = $('.next');
    var $slideprevious = $('.previous');
    var itemwidth = 0;
    var slidefactor = 1;
    var $lazyImgs = $('a.product img');

    function slide(direction) {
        if (running) return;
        running = true;
        if (embed_type == 'single') {
            index -= direction;
        } else {
            slidefactor = visiblechildren*2 <= $items.length ? visiblechildren : $items.length - visiblechildren;
            index -= slidefactor*direction;
        }
        if (index < 0) {
            for (var i=0;i<-1*index;i++) {
                $ul.children('li').last().detach().prependTo($ul);
            }
            $ul.css('left', -1*slidefactor*itemwidth + 'px');
            // adjust index
            index = 0;
            $items = $ul.children('li');
        } else if (index + visiblechildren > $items.length || ($ul.width() + direction*itemwidth*slidefactor + $ul.position().left < $container.width())) {
            var diff = index+visiblechildren-$items.length;
            for (var i=0;i<diff;i++) {
                $ul.children('li').first().detach().appendTo($ul);
            }
            $ul.css('left', $ul.position().left + diff*itemwidth + 'px');
            // adjust index
            index = $items.length - visiblechildren;
            $items = $ul.children('li');
        }
        $ul.animate({'left': '+=' + slidefactor*direction*itemwidth}, {'complete': function() { running = false; $lazyImgs = loadImgs($lazyImgs) }});
    }

    var mc = new Hammer($('.slidecontainer')[0]);
    mc.on('swipeleft swiperight', function(e) { if (!doslide) return; slide(e.type == 'swipeleft' ? -1 : 1); });

    function enableslide() {
        if (!doslide) {
            $slideprevious.on('click', function () {
                slide(1);
            });
            $slidenext.on('click', function () {
                slide(-1);
            });
        }
        $slidenext.parent().show();
        doslide = true;
    }

    function disableslide() {
        $('.previous').off('click');
        $('.next').off('click').parent().hide();
        doslide = false;
    }

    function resize() {
        var $window = $(window);
        var $this;
        var imgratio;
        var maxheight = 0;
        var $images = $('a.product img');
        var childwidth = 0;
        var margin = 120;
        var captionheight = $('.caption').length ? $('.caption').first().height() + 10 : 0;

        $('.slidecontainer, .productcontainer').css({height: 'auto', width: $window.width() + (padding * 2)});

        $images.each(function(item, i) {
            $this = $(this);
            imgratio = $this.attr('width')/$this.attr('height');
            if (imgratio > 1 && $window.width()/$window.height() < 1) {
                if (width > $window.width()) width = $window.width();
                $this.css({'width': width, height: Math.round($(this).attr('height')/$(this).attr('width')*width)});
            } else {
                $this.css({height: $window.height() - captionheight, width: Math.round($(this).attr('width')/$(this).attr('height')*($window.height()-captionheight))});
            }
            maxheight = Math.max(maxheight, $this.height());
            childwidth = Math.max(childwidth, $this.width());
        });

        if ((childwidth + margin + padding) > $window.width()) {
            var width = ($window.width() - margin - padding);
            imgratio = $this.attr('width')/$this.attr('height');
            width = (width/imgratio - captionheight) * imgratio;
            $images.each(function(item, i) {
                $(this).css({width: width, height: 'auto'});
            });
            childwidth = width;
        }

        itemwidth = $items.first().width() + padding;

        if (embed_type == 'single') {
            $container.width(itemwidth);
            if ($items.length > 1) {
                enableslide();
            } else {
                disableslide();
            }
            visiblechildren = 1;
        } else {
            visiblechildren = Math.floor(($window.width() - margin)/(itemwidth));
            $container.width(visiblechildren*(itemwidth));
            if (Math.floor(visiblechildren) < $items.length) {
                enableslide();
            } else {
                disableslide()
            }
        }
        $ul.children('li').css('width', itemwidth);
        index = 0;
        $ul.css('left', 0);
        var containermargin = parseInt($container.css('marginLeft').substr(0, $container.css('marginLeft').length -2));
        $slideprevious.css({left: Math.max(10, containermargin-$slideprevious.width() - 10)});
        $slidenext.css({right: Math.max(10, containermargin-$slideprevious.width() - 10)});
        // Set width of list
        $ul.width($items.length * itemwidth);
        $lazyImgs = loadImgs($lazyImgs)
    }

    enableslide();
    $(window).on('resize', resize);
    resize();

    function trackEvent(category, action) {
        return function() {
            var el = $(this),
                sid = el.attr('data-sid'),
                slug = el.attr('data-slug'),
                vendor = el.attr('data-vendor'),
                price = parseInt(el.attr('data-price'), 10);

            ga('send', 'event', category, action, sid + ' - ' + vendor + ' - ' + slug, price);
            _gaq.push(['_trackEvent', category, action, sid + ' - ' + vendor + ' - ' + slug, price]);

            return true;
        }
    }

    $(document).on('click', 'body.product-widget-embed a.btn-buy-external', trackEvent('Ext-Look', 'BuyReferral'));
});
