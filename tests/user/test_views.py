#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Zhang Yungui
@time: 2018/6/12
"""
from tests.testcase import APITestCase
from controller.views import handlers
import re

admin = 'admin@test.com', 'test123'
user1 = 't1@test.com', 't12345'


class TestViews(APITestCase):

    def _test_view(self, url):
        if '(' not in url:
            r = self.parse_response(self.fetch(url))
            self.assertTrue('currentUserId' in r, url + re.sub(r'(\n|\s)+', '', r)[:120])

    def test_with_admin(self):
        r = self.fetch('/api/user/login', body={'data': dict(email=admin[0], password=admin[1])})
        if self.get_code(r) == 200:
            for view in handlers:
                if isinstance(view.URL, list):
                    for url in view.URL:
                        self._test_view(url)
                else:
                    self._test_view(view.URL)

    def test_with_any_user(self):
        r = self.fetch('/api/user/login', body={'data': dict(email=user1[0], password=user1[1])})
        if self.get_code(r) == 200:
            for view in handlers:
                if isinstance(view.URL, list):
                    for url in view.URL:
                        self._test_view(url)
                else:
                    self._test_view(view.URL)

    def test_404(self):
        r = self.parse_response(self.fetch('/xyz'))
        self.assertIn('404', r)
        r = self.fetch('/api/xyz')
        self.assertNotIn('404', self.parse_response(r))
        self.assert_code(404, r)

    def test_show_api(self):
        r = self.parse_response(self.fetch('/api'))
        self.assertNotIn('None', r)
