#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/6/12
"""
from tests.testcase import APITestCase
from controller.views import handlers
from controller.role import role_route_maps
from itertools import chain
import re

admin = 'admin@test.com', 'test123'
user1 = 't1@test.com', 't12345'


class TestViews(APITestCase):
    ROUTES = list(chain(*(list(v.get('routes', {}).keys()) for v in role_route_maps.values())))

    def _test_view(self, url, errors=None):
        if '(' not in url:
            r = self.parse_response(self.fetch(url))
            self.assertTrue('currentUserId' in r, msg=url + re.sub(r'(\n|\s)+', '', r)[:120])
            self.assertFalse('访问出错' in r, msg=url)

        # 确保每个前端路由都设置了角色
        if errors is not None and url not in self.ROUTES:
            errors.append(url + ' no role')

    def test_with_admin(self):
        r = self.fetch('/api/user/login', body={'data': dict(email=admin[0], password=admin[1])})
        if self.get_code(r) == 200:
            for view in handlers:
                if isinstance(view.URL, list):
                    for url in view.URL:
                        self._test_view(url)
                elif isinstance(view.URL, str):
                    self._test_view(view.URL)

    def test_with_any_user(self):
        r = self.fetch('/api/user/login', body={'data': dict(email=user1[0], password=user1[1])})
        if self.get_code(r) == 200:
            errors = []
            for view in handlers:
                if isinstance(view.URL, list):
                    for url in view.URL:
                        self._test_view(url, errors)
                elif isinstance(view.URL, str):
                    self._test_view(view.URL, errors)
            self.assertFalse(errors)

    def test_404(self):
        # 访问不存在的前端网页将显示404页面
        r = self.parse_response(self.fetch('/xyz'))
        self.assertIn('404', r)

        # 访问不存在的API接口将返回404的空结果而不是网页
        r = self.fetch('/api/xyz')
        rs = self.parse_response(r)
        self.assert_code(404, r)
        self.assertFalse(rs)

    def test_show_api(self):
        r = self.parse_response(self.fetch('/api?_raw=1'))
        self.assertIn('handlers', r)
        for url, func, comment, auth in r['handlers']:
            self.assertTrue(auth, '%s %s need roles' % (url, func))
            self.assertNotIn(comment, ['', 'None', None], '%s %s need doc comment' % (url, func))

    def test_profile(self):
        self.assert_code(200, self.login('text1@test.com', 't12345'))
        r = self.parse_response(self.fetch('/user/profile'))
        self.assertIn('text1@test.com', r)
