// Standard Google Universal Analytics code
(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
})(window,document,'script','https://www.google-analytics.com/analytics.js','ga'); // Note: https protocol here

ga('create', 'UA-21990268-2', 'auto');
ga('set', 'checkProtocolTask', function(){}); // Removes failing protocol check. @see: http://stackoverflow.com/a/22152353/1958200
ga('require', 'displayfeatures');
ga('send', 'pageview', '/chrome-extension.html');


var DOMAIN = 'http://apprl.com';

var AUTHENTICATED_URL = DOMAIN + '/backend/authenticated/';
var PRODUCT_URL = DOMAIN + '/backend/product/lookup/';
var LOGIN_URL = DOMAIN + '/en/accounts/login/';

function getCookies(domain, name, callback) {
  chrome.cookies.get({"url": domain, "name": name}, function(cookie) {
    if(callback) {
      callback(cookie.value);
    }
  });
}


/**
 * Is authenticated XHR-request
 */
function isAuthenticated(callback) {
  var xhr = new XMLHttpRequest();
  xhr.open('GET', AUTHENTICATED_URL, true);
  xhr.onreadystatechange = function() {
    if (xhr.readyState == 4) {
      callback(JSON.parse(xhr.responseText));
    } 
  }
  xhr.send();
}


/**
 * Fetch product XHR-request
 */
function fetchProduct(product, domain, isProduct, callback) {
  var xhr = new XMLHttpRequest();
  var requestURL = PRODUCT_URL + '?key=' + encodeURIComponent(product) + '&domain=' + encodeURIComponent(domain);
  if (isProduct)
    requestURL += '&is_product=' + isProduct;
  console.log(requestURL);
  xhr.open('GET', requestURL , true);
  xhr.onreadystatechange = function() {
    if (xhr.readyState == 4) {
      var parsed = {};
      try {
        parsed = JSON.parse(xhr.responseText);
      } catch(error) {}
      callback(parsed);
    }
  }
  xhr.send();
}


/**
 * Like product XHR-request
 */
function likeProductRequest(product, action, callback) {
  getCookies(DOMAIN, 'csrftoken', function(csrftoken) {
    var xhr = new XMLHttpRequest();
    xhr.open('POST', DOMAIN + '/products/' + product + '/' + action + '/', true);
    xhr.setRequestHeader("X-CSRFToken", csrftoken);
    xhr.onreadystatechange = function() {
      if (xhr.readyState == 4) {
        var parsed = {};
        try {
          parsed = JSON.parse(xhr.responseText);
        } catch(error) {}
        callback(parsed);
      } 
    }
    xhr.send();
  });
}

/*
 * Send fetchProduct XHR-request
 */
function fetchProductFromServer(currentTabURL, isProduct){
  var profileLink = document.querySelector('.profile-link');
  profileLink.onclick = function() {
    chrome.tabs.create({active: true, url: response.profile});
  };

  var body = document.querySelector('body');
  var buttons = document.querySelector('.buttons');
  var likeButton = document.querySelector('.like-button');
  var productButton = document.querySelector('.product-button');
  var productLink = document.querySelector('.product-link');
  var productName = document.querySelector('.product-name');
  var productEarning = document.querySelector('.product-earning');
  var productShortLink = document.querySelector('.product-short-link');
  var productShortLinkInput = document.querySelector('.product-short-link input');
  var noLikeText = document.querySelector('.no-like');

  body.className = 'semi-active';

  var hostname = '';
  var url = new URL(currentTabURL)

  if (url) {
    hostname = url.hostname;
  }
  fetchProduct(currentTabURL, hostname, isProduct, function(response) {
    body.className = 'active';
    if (response.product_short_link) {

      var likeButtonClass = ' disabled';
      if (response.product_link) {
        ga('send', 'event', 'ChromeExtension', 'LoadURL', currentTabURL.url); // Send event to GA on product link load
        likeButtonClass = '';
      } else {
        ga('send', 'event', 'ChromeExtension', 'LoadDomain', hostname); // Send event to GA on domain load
        noLikeText.className = 'no-like show'; // Show no-like text
      }

      if (response.product_liked) {
        likeButton.className = 'like-button liked' + likeButtonClass;
      } else {
        likeButton.className = 'like-button' + likeButtonClass;
      }
      productButton.className = 'product-button';

      if (response.product_link) {
        productLink.className = 'product-link bold';
        productLink.href = response.product_link;
      }
      productShortLinkInput.value = response.product_short_link;

      if (response.product_link) {
        var likeActive = false;
        likeButton.onclick = function() {
          ga('send', 'event', 'ChromeExtension', 'ProductLike', currentTabURL.url); // Send event to GA on like button click
          if (likeActive === false) {
            likeActive = true;
            if (response.product_liked) {
              var action = 'unlike';
              likeButton.className = 'like-button';
            } else {
              var action = 'like';
              likeButton.className = 'like-button liked';
            }
            likeProductRequest(response.product_pk, action, function() {
              likeActive = false;
              response.product_liked = (action === 'like' ? true : false);
            });
          }
        };
      }

      if (response.product_name) {
        productName.className = 'product-name bold';
        productName.textContent = response.product_name;
      }

      if (response.product_earning) {
        productEarning.className = 'product-earning';
        productEarning.textContent = response.product_earning;
      }

      productButton.onclick = function() {
        ga('send', 'event', 'ChromeExtension', 'ClickGetLinkButton', currentTabURL.url); // Send event to GA on product link button click
        noLikeText.className = 'no-like'; // Hide no-like text
        if (productShortLinkInput.value) {
          productShortLink.style.display = 'block';
        }
      };
    } else {
      buttons.style.display = 'none';
      document.querySelector('.no-hit').className = 'no-hit';
    }
  });
}


/**
 * Get source code for current tab
 */
function getSourceCode(currentTabURL) {
  var xhr = new XMLHttpRequest();
  xhr.open('GET', currentTabURL, true);
  xhr.onreadystatechange = function() {
    if (xhr.readyState == 4) {
      var parser = new DOMParser();
      var isProduct = 0;
      try {
        html = parser.parseFromString(xhr.responseText, "text/html");
        if (html.getElementById("productPage"))
          isProduct = 1;
      } catch(error) {}
      fetchProductFromServer(currentTabURL, isProduct);
    }
  };
  xhr.send();
}


/**
 * Get current chrome tab
 */
function run(response) {
  // Fetch product based on URL
  chrome.tabs.query({currentWindow: true, active: true}, function(tabs) {
    getSourceCode(tabs[0].url);
  });
}


/**
 * Initialize and check authentication
 */

document.addEventListener('DOMContentLoaded', function() {
  isAuthenticated(function(response) {
    if (response.authenticated === true) {
      run(response);
    } else {
      chrome.tabs.create({url: LOGIN_URL});
    }
  });
});