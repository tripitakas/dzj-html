#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Zhang Yungui
@time: 2018/12/22
"""
from tornado.escape import json_decode, json_encode, native_str
from tornado.options import options
from tornado.testing import AsyncHTTPSTestCase
from tornado.httpclient import HTTPRequest
from tornado.util import PY3
import re
from controller.api import handlers
from controller.app import Application

if PY3:
    import http.cookies as Cookie
else:
    import Cookie

cookie = Cookie.SimpleCookie()


class APITestCase(AsyncHTTPSTestCase):

    def get_app(self):
        options.debug = False
        options.port = self.get_http_port()
        return Application(handlers, db_name_ext='_test')

    @staticmethod
    def parse_response(response):
        return response.body and json_decode(response.body) or {}

    def assert_code(self, code, response):
        code = code[0] if isinstance(code, tuple) else code
        response = self.parse_response(response)
        response_code = response.get('code', 200)
        if isinstance(code, list):
            self.assertIn(response_code, [c[0] if isinstance(c, tuple) else c for c in code])
        else:
            self.assertEqual(code, response_code, response.get('error'))

    def fetch(self, url, **kwargs):
        if isinstance(kwargs.get('body'), dict):
            if isinstance(kwargs['body'].get('data'), dict):
                kwargs['body']['data'] = json_encode(kwargs['body']['data'])
            kwargs['body'] = json_encode(kwargs['body'])
            kwargs['method'] = kwargs.get('method', 'POST')

        headers = kwargs.get('headers', {})
        headers['Cookie'] = ''.join(['%s=%s;' % (x, morsel.value) for (x, morsel) in cookie.items()])

        request = HTTPRequest(self.get_url(url), headers=headers, **kwargs)
        self.http_client.fetch(request, self.stop)

        response = self.wait(timeout=2)
        headers = response.headers
        try:
            sc = headers._dict['Set-Cookie'] if hasattr(headers, '_dict') else headers['Set-Cookie']
            text = native_str(sc)
            text = re.sub(r'Path=/(,)?', '', text)
            cookie.update(Cookie.SimpleCookie(text))
            while True:
                cookie.update(Cookie.SimpleCookie(text))
                if ',' not in text:
                    break
                text = text[text.find(',') + 1:]
        except KeyError:
            pass

        return response
