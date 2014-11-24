
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
function fetchProduct(product, domain, callback) {
  var xhr = new XMLHttpRequest();
  xhr.open('GET', PRODUCT_URL + '?key=' + encodeURIComponent(product) + '&domain=' + encodeURIComponent(domain), true);
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




function run(response) {
  var profileLink = document.querySelector('.profile-link');
  profileLink.onclick = function() {
    chrome.tabs.create({active: true, url: response.profile});
  };

  var body = document.querySelector('body');
  var buttons = document.querySelector('.buttons');
  var likeButton = document.querySelector('.like-button');
  var productButton = document.querySelector('.product-button');
  var productLink = document.querySelector('.product-link');
  var productShortLink = document.querySelector('.product-short-link');
  var productShortLinkInput = document.querySelector('.product-short-link input');

  body.className = 'semi-active';

  // Fetch product based on URL
  chrome.tabs.query({currentWindow: true, active: true}, function(tabs) {

    var hostname = '';
    var url = new URL(tabs[0].url)
    if (url) {
      hostname = url.hostname;
    }

    fetchProduct(tabs[0].url, hostname, function(response) {
      body.className = 'active';
      if (response.product_short_link) {

        var likeButtonClass = ' disabled';
        if (response.product_link) {
          likeButtonClass = '';
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

        productButton.onclick = function() {
          if (productShortLinkInput.value) {
            productShortLink.style.display = 'block';
          }
        };
      } else {
        buttons.style.display = 'none';
        document.querySelector('.no-hit').className = 'no-hit';
      }
    });
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
