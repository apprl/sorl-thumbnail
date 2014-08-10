
var DOMAIN = 'http://dev-apprl.xvid.se';

var AUTHENTICATED_URL = DOMAIN + '/backend/authenticated/';
var PRODUCT_URL = DOMAIN + '/backend/product/lookup/';
var LOGIN_URL = DOMAIN + '/en/accounts/login/';


/**
 * Is authenticated XHR-request
 */
function isAuthenticated(callback) {
  var xhr = new XMLHttpRequest();
  xhr.open("GET", AUTHENTICATED_URL, true);
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
  xhr.open("GET", PRODUCT_URL + '?key=' + encodeURIComponent(product), true);
  xhr.onreadystatechange = function() {
    if (xhr.readyState == 4) {
      callback(JSON.parse(xhr.responseText));
    } 
  }
  xhr.send();
}


/**
 * Like product XHR-request
 */
function likeProduct(product, callback) {
  // TODO: like product...
}




function run(response) {
  var profileLink = document.querySelector('.profile-link');
  profileLink.onclick = function() {
    chrome.tabs.create({active: true, url: DOMAIN + response.profile});
  };

  var likeButton = document.querySelector('.like-button');
  var productButton = document.querySelector('.product-button');
  var productLink = document.querySelector('.product-link');
  var productShortLink = document.querySelector('.product-short-link');
  var productShortLinkInput = document.querySelector('.product-short-link input');

  likeButton.onclick = function() {
    // TODO: do like request on product data
  };

  productButton.onclick = function() {
    if (productShortLinkInput.value) {
      productShortLink.style.display = 'block';
    }
  };

  chrome.tabs.query({currentWindow: true, active: true}, function(tabs) {
    // Fetch product based on URL
    fetchProduct(tabs[0].url, function(response) {
      if (response.product_short_link) {
        productButton.className = 'product-button';
        likeButton.className = 'like-button';
        productLink.className = 'product-link';
        productLink.href = response.product_link;
        productShortLinkInput.value = response.product_short_link;
      }
    });
  });
}


/**
 * Initialize and check authentication
 */

document.addEventListener('DOMContentLoaded', function() {
  var body = document.querySelector('body');
  isAuthenticated(function(response) {
    if (response.authenticated === true) {
      body.className = 'active';
      run(response);
    } else {
      chrome.tabs.create({url: LOGIN_URL});
    }
  });
});
