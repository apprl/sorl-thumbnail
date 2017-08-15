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
    var visibleChildren;
    var doSlide = false;
    var $container = $('.slidecontainer');
    var navigationWidth = 60;
    var $slideNext = $('.next');
    var $slidePrevious = $('.previous');
    var itemWidth = 0;
    var slideFactor = 1;
    var $lazyImgs = $('a.product img');

    function slide(direction) {
        if (running) return;
        running = true;
        if (embed_type == 'single') {
            index -= direction;
        } else {
            slideFactor = visibleChildren*2 <= $items.length ? visibleChildren : $items.length - visibleChildren;
            index -= slideFactor*direction;
        }
        if (index < 0) {
            for (var i=0;i<-1*index;i++) {
                $ul.children('li').last().detach().prependTo($ul);
            }
            $ul.css('left', -1*slideFactor*itemWidth + 'px');
            // adjust index
            index = 0;
            $items = $ul.children('li');
        } else if (index + visibleChildren > $items.length || ($ul.width() + direction*itemWidth*slideFactor + $ul.position().left < $container.width())) {
            var diff = index+visibleChildren-$items.length;
            for (var i=0;i<diff;i++) {
                $ul.children('li').first().detach().appendTo($ul);
            }
            $ul.css('left', $ul.position().left + diff*itemWidth + 'px');
            // adjust index
            index = $items.length - visibleChildren;
            $items = $ul.children('li');
        }
        $ul.animate({'left': '+=' + slideFactor*direction*itemWidth}, {'complete': function() { running = false; $lazyImgs = loadImgs($lazyImgs) }});
    }

    var mc = new Hammer($('.slidecontainer')[0]);
    mc.on('swipeleft swiperight', function(e) { if (!doSlide) return; slide(e.type == 'swipeleft' ? -1 : 1); });

    function enableSlide() {
        if (!doSlide) {
            $slidePrevious.on('click', function () {
                slide(1);
            });
            $slideNext.on('click', function () {
                slide(-1);
            });
        }
        $slideNext.parent().show();
        doSlide = true;
    }

    function disableSlide() {
        $('.previous').off('click');
        $('.next').off('click').parent().hide();
        doSlide = false;
    }

    function resize() {
        var $window = $(window);
        var winWidth = $window.width() - navigationWidth;
        var $this;
        var imgRatio;
        var maxHeight = 0;
        var $images = $('a.product img');
        var childWidth = 0;
        var padding = 10;
        var captionHeight = $('.caption').length ? $('.caption').first().height() + 10 : 0;
        var numItemsPerSlide = winWidth > 1450 ? 8 : winWidth > 1160 ? 6 : winWidth > 870 ? 5 : winWidth > 580 ? 4 : winWidth > 400 ? 3 : 2;

        if (embed_type === 'single') {
            numItemsPerSlide = 1;
        }

        itemWidth = Math.round(winWidth / numItemsPerSlide);
        $items.width(itemWidth)
        $ul.width($items.length * itemWidth);
        $container.css({height: 'auto', width: winWidth});

        $images.each(function(item, i) {
            $this = $(this);
            imgRatio = $this.attr('width')/$this.attr('height');
            if (imgRatio > 1 && $window.width()/$window.height() < 1) {
                if (width > $window.width()) width = $window.width();
                $this.css({'width': width, height: Math.round($(this).attr('height')/$(this).attr('width')*width)});
            } else {
                var newHeight = $window.height() - captionHeight;
                var newWidth = Math.round($(this).attr('width')/$(this).attr('height') * newHeight) - padding;
                $this.css({height: 'auto', width: newWidth });
            }
            maxHeight = Math.max(maxHeight, $this.height());
            childWidth = Math.max(childWidth, $this.width());
        });

        if ((childWidth) > $window.width()) {
            var width = ($window.width());
            imgRatio = $this.attr('width')/$this.attr('height');
            width = (width/imgRatio - captionHeight) * imgRatio;
            $images.each(function(item, i) {
                $(this).css({width: width, height: 'auto'});
            });
            childWidth = width;
        }

        if (embed_type == 'single') {
            $container.width(itemWidth);
            if ($items.length > 1) {
                enableSlide();
            } else {
                disableSlide();
            }
            visibleChildren = 1;
        } else {
            visibleChildren = Math.floor(($window.width())/(itemWidth));
            $container.width(visibleChildren*(itemWidth));
            if (Math.floor(visibleChildren) < $items.length) {
                enableSlide();
            } else {
                disableSlide()
            }
        }
        index = 0;
        $ul.css('left', 0);
        $lazyImgs = loadImgs($lazyImgs)
    }

    enableSlide();
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
