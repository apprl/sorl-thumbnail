// From http://detectmobilebrowsers.com/
function is_mobile() {
    var ua = navigator.userAgent||navigator.vendor||window.opera;
    if(/android.+mobile|avantgo|bada\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|meego.+mobile|midp|mmp|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\.(browser|link)|vodafone|wap|windows (ce|phone)|xda|xiino/i.test(ua)||/1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\-(n|u)|c55\/|capi|ccwa|cdm\-|cell|chtm|cldc|cmd\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\-s|devi|dica|dmob|do(c|p)o|ds(12|\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\-|_)|g1 u|g560|gene|gf\-5|g\-mo|go(\.w|od)|gr(ad|un)|haie|hcit|hd\-(m|p|t)|hei\-|hi(pt|ta)|hp( i|ip)|hs\-c|ht(c(\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\-(20|go|ma)|i230|iac( |\-|\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\/)|klon|kpt |kwc\-|kyo(c|k)|le(no|xi)|lg( g|\/(k|l|u)|50|54|\-[a-w])|libw|lynx|m1\-w|m3ga|m50\/|ma(te|ui|xo)|mc(01|21|ca)|m\-cr|me(di|rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\-2|po(ck|rt|se)|prox|psio|pt\-g|qa\-a|qc(07|12|21|32|60|\-[2-7]|i\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\-|oo|p\-)|sdk\/|se(c(\-|0|1)|47|mc|nd|ri)|sgh\-|shar|sie(\-|m)|sk\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\-|v\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\-|tdg\-|tel(i|m)|tim\-|t\-mo|to(pl|sh)|ts(70|m\-|m3|m5)|tx\-9|up(\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\-|your|zeto|zte\-/i.test(ua.substr(0,4))) {
          return true;
      }
      return false;
}

function getParameterByName(name) {
    name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
        results = regex.exec(location.search);
    return results === null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
}

jQuery(document).ready(function() {
    var parentHost = getParameterByName('host');

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

    function slide(direction) {
        if (running) return;
        running = true;
        index -= direction;
        if (index < 0) {
            $items.last().detach().prependTo($ul);
            $ul.css('left', ($ul.position().left - itemwidth) + 'px');
            index = 0;
            $items = $ul.children('li');
        } else if (index + visiblechildren > $items.length || ($ul.width() + direction*itemwidth + $ul.position().left < $container.width())) {
            $items.first().detach().appendTo($ul);
            $ul.css('left', ($ul.position().left + itemwidth) + 'px');
            index -= 1;
            $items = $ul.children('li');
        }

        $ul.animate({'left': '+=' + direction*itemwidth}, {'complete': function() { running = false; }});
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
        $('.navigation').width($window.width());
        var captionheight = $('.caption').length ? $('.caption').first().height() + 10 : 0;

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
            $ul.css('left', -1*index*itemwidth);
        } else {
            $container.width($window.width() - margin);
            visiblechildren = Math.floor($container.width()/(itemwidth+padding));
            if (Math.floor(visiblechildren) < $items.length) {
                enableslide();
            } else {
                disableslide()
            }
            $ul.css('left', ($container.width() - $items.length*(itemwidth))/2);
        }

        var containermargin = parseInt($container.css('marginLeft').substr(0, $container.css('marginLeft').length -2));
        // Set width of list
        $ul.width($items.length * itemwidth);
        $slideprevious.css({left: Math.max(10, containermargin-$slideprevious.width() - 10), top: (($container.height()-captionheight - $slidenext.height())/2)+'px'});
        $slidenext.css({right: Math.max(10, containermargin-$slideprevious.width() - 10), top: (($container.height()-captionheight - $slidenext.height())/2)+'px'});
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
