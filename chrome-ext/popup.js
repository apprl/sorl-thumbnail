
var DOMAIN = 'http://dev-apprl.xvid.se';

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
function fetchProduct(product, callback) {
  var xhr = new XMLHttpRequest();
  xhr.open('GET', PRODUCT_URL + '?key=' + encodeURIComponent(product), true);
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
function likeProductRequest(product, callback) {
  getCookies(DOMAIN, 'csrftoken', function(csrftoken) {
    var xhr = new XMLHttpRequest();
    xhr.open('POST', DOMAIN + '/products/' + product + '/like/', true);
    xhr.setRequestHeader("X-CSRFToken", csrftoken);
    xhr.onreadystatechange = function() {
      if (xhr.readyState == 4) {
        callback(JSON.parse(xhr.responseText));
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
  var likeButton = document.querySelector('.like-button');
  var likeButtonText = document.querySelector('.like-button span:first-child');
  var productButton = document.querySelector('.product-button');
  var productLink = document.querySelector('.product-link');
  var productShortLink = document.querySelector('.product-short-link');
  var productShortLinkInput = document.querySelector('.product-short-link input');

  // Fetch product based on URL
  chrome.tabs.query({currentWindow: true, active: true}, function(tabs) {
    fetchProduct(tabs[0].url, function(response) {
      body.className = 'active';
      if (response.product_short_link) {
        if (response.product_liked) {
          likeButtonText.innerText = 'Liked';
          likeButton.className = 'like-button liked';
        } else {
          likeButtonText.innerText = 'Like';
          likeButton.className = 'like-button';
        }
        productButton.className = 'product-button';
        productLink.className = 'product-link';
        productLink.href = response.product_link;
        productShortLinkInput.value = response.product_short_link;

        likeButton.onclick = function() {
          likeProductRequest(response.product_pk);
          likeButtonText.innerText = 'Liked';
          likeButton.className = 'like-button liked';
        };

        productButton.onclick = function() {
          if (productShortLinkInput.value) {
            productShortLink.style.display = 'block';
          }
        };
      } else {
        document.querySelector('.no-hit').className = 'no-hit';
        likeButtonText.innerText = 'Like';
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
