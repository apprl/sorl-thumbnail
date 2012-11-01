(function($) {

  var Apprl = {
    // Stylesheet string to be included on target page
    styleString: '.apprl_look{overflow:hidden;clear:both;}\n.apprl_look div{line-height:20px;}\n.apprl_link{font-family:"Helvetica Neue","Helvetica","Arial",sans-serif;font-size:12px;color:#000;text-decoration:none;}\n.apprl_left{float:left;padding-left:5px;}\n.apprl_right{float:right;padding-right:5px;}',

    // Attach stylesheet string on target page
    attachStyle: function() {
      if (document.createStyleSheet) {
        try {
          document.createStyleSheet().cssText = Apprl.styleString;
        } catch (error) {
          if (document.styleSheets[0]) {
            document.styleSheets[0].cssText += Apprl.styleString;
          }
        }
      } else {
        var style = document.createElement('style');
        style.type = 'text/css';
        style.textContent = Apprl.styleString;
        document.getElementsByTagName('head')[0].appendChild(style);
      }
    },

    // Run initialize code on ready DOM
    ready: function() {
      Apprl.attachStyle();

      $('.apprl_look').each(function(index, elem) {
        var $elem = $(elem);

        // Width
        var width = $elem.data('width');
        if (width == 'auto') {
          width = $elem.width();
        }

        // Height
        var height = $elem.data('height');
        if (height == 'auto') {
          //height = $elem.height();
          height = 546;
        }

        elem.style.width = width;

        // Iframe
        var iframe = document.createElement('iframe');
        iframe.src = $(elem).data('href');
        iframe.width = width - 2; // Border
        iframe.height = height - 20; // Footer
        iframe.frameBorder = 0;
        iframe.scrolling = 'no';

        // Footer
        var footer = document.createElement('div');
        footer.style.width = width;
        footer.style.height = 20;

        // Footer - user link
        if ($elem.data('user-href')) {
          var user = document.createElement('a');
          user.href = $elem.data('user-href');
          user.className = 'apprl_left apprl_link';
          user.innerHTML = '+ follow me';
          footer.appendChild(user);
        }

        var home = document.createElement('a');
        home.href = 'http://apprl.com/';
        home.className = 'apprl_right apprl_link'
        home.innerHTML = '\\ powered by APPRL';
        footer.appendChild(home);

        $(elem).append(iframe).append(footer);
      });

    }
  };

  $(document).ready(Apprl.ready);

})(jQuery.noConflict());
