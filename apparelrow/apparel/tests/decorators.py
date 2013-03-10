from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed, HttpResponseForbidden, HttpResponseNotFound
from django.test import TestCase, Client
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required

from apparelrow.apparel.decorators import *

import json

@seamless_request_handling
def view_func(request, rval):
    if rval == 'ok':
        return HttpResponse('<b>html</b>')
    
    if rval == 'tuple':
        return ({ 'blah': 'hej' }, HttpResponseRedirect('http://www.example.com'))
    
    if rval == 'forbidden':
        return HttpResponseForbidden()
    
    if rval == 'notfound':
        raise ObjectDoesNotExist()

@seamless_request_handling
@login_required
def view_func_auth(request):
    return HttpResponse()

class TestDecorators(TestCase):
    urls = 'apparel.tests.urls'
    
    def test_decorator_200(self):
        r = self.client.get('/decorator/ok/', {})
        
        self.assertEqual(r.status_code, 200, 'Got repsonse')
    
    def test_decorator_200_ajax(self):
        r = self.client.get('/decorator/ok/', {}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertTrue(isinstance(r, HttpResponse), 'Got 200')
        self.assertEquals(r['Content-Type'], 'application/json')
        
        try:
            content = json.loads(r.content)
        except Exception, e:
            self.fail('Cannot parse JSON')
        
        
        self.assertEquals(content['success'], True, 'Status set to true')    
        
        
    def test_decorator_tuple(self):
        r = self.client.get('/decorator/tuple/', {})
        
        self.assertTrue(isinstance(r, HttpResponseRedirect), 'Got the HTTP response')
        self.assertEqual(r['Location'], 'http://www.example.com')
    
    def test_decorator_tuple_ajax(self):
        r = self.client.get('/decorator/tuple/', {}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertTrue(isinstance(r, HttpResponse), 'Got 200')
        self.assertEquals(r['Content-Type'], 'application/json')
        
        try:
            content = json.loads(r.content)
        except Exception, e:
            self.fail('Cannot parse JSON')
        
        self.assertEquals(content['success'], True, 'Status set to true')
        self.assertEquals(content['data'], { 'blah': 'hej'}, 'Got serialised content')
    
    def test_decorator_forbidden(self):
        r = self.client.get('/decorator/forbidden/', {}, HTTP_REFERER='/cock')
        
        self.assertTrue(isinstance(r, HttpResponseRedirect), 'Forbidden generates redirect')
        self.assertEqual(r['Location'], 'http://testserver%s?next=/cock' % settings.LOGIN_URL)

    def test_decorator_forbidden_ajax(self):
        r = self.client.get('/decorator/forbidden/', {}, HTTP_REFERER='/cock', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertTrue(isinstance(r, HttpResponse), 'Got 200')
        
        try:
            content = json.loads(r.content)
        except Exception, e:
            self.fail('Cannot parse JSON')
        
        self.assertEquals(content['success'], False, 'Status set to false')
        self.assertEquals(content['error_message'], 403)
        self.assertEquals(content['location'], '%s?next=/cock' % settings.LOGIN_URL)
    
    def test_decorator_notfound(self):
        r = self.client.get('/decorator/notfound/', {})
        
        self.assertTrue(isinstance(r, HttpResponseNotFound), 'ObjectDoesNotExist causes 404')
    
    def test_decorator_notfound_ajax(self):
        r = self.client.get('/decorator/notfound/', {}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertTrue(isinstance(r, HttpResponse), 'Got 200')
        
        try:
            content = json.loads(r.content)
        except Exception, e:
            self.fail('Cannot parse JSON')
        
        self.assertEquals(content['success'], False, 'Status set to false')
        self.assertEquals(content['error_message'], 404)
    
   
    def test_decorator_auth(self):
        r = self.client.get('/decorator/auth/', {})
        
        self.assertTrue(isinstance(r, HttpResponseRedirect), 'login_required decorator')
        self.assertEqual(r['Location'], 'http://testserver%s?next=/decorator/auth/' % settings.LOGIN_URL)

    def test_decorator_auth_ajax(self):
        r = self.client.get('/decorator/auth/', {}, HTTP_REFERER='/cock', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertTrue(isinstance(r, HttpResponse), 'login_required decorator output caught')
        
        try:
            content = json.loads(r.content)
        except Exception, e:
            self.fail('Cannot parse JSON')
        
        self.assertEquals(content['success'], False, 'Status set to false')
        self.assertEquals(content['error_message'], 302)
        self.assertEquals(content['location'], '%s?next=/decorator/auth/' % settings.LOGIN_URL)
