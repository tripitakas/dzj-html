#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/6/12
"""
from tests.testcase import APITestCase
from controller.user import views
import re

admin = 'admin@test.com', 'test123'
user1 = 't1@test.com', 't12345'


class TestViews(APITestCase):
    def _test_view(self, url, check_role):
        if '(' not in url:  # URL不需要动态参数
            r = self.parse_response(self.fetch(url + '?_no_auth=1'))
            self.assertTrue('currentUserId' in r, msg=url + re.sub(r'(\n|\s)+', '', r)[:120])
            if check_role and '访问出错' in r:
                self.assertFalse('访问出错' in r, msg=url)

    def test_with_admin(self):
        r = self.fetch('/api/user/login', body={'data': dict(email=admin[0], password=admin[1])})
        if self.get_code(r) == 200:
            for view in views:
                if isinstance(view.URL, list):
                    for url in view.URL:
                        self._test_view(url, True)
                elif isinstance(view.URL, str):
                    self._test_view(view.URL, True)

    def test_with_any_user(self):
        r = self.fetch('/api/user/login', body={'data': dict(email=user1[0], password=user1[1])})
        if self.get_code(r) == 200:
            for view in views:
                if isinstance(view.URL, list):
                    for url in view.URL:
                        self._test_view(url, False)
                elif isinstance(view.URL, str):
                    self._test_view(view.URL, False)

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
        for url, func, file, comment, auth in r['handlers']:
            # 要求URL已登记到角色路由映射表中
            # self.assertTrue(auth, '%s %s need roles' % (url, func))
            # 控制器类的get/post方法需要写简要的文档字符串
            self.assertNotIn(comment, ['', 'None', None], '%s %s need doc comment' % (url, func))

    def test_profile(self):
        self.add_users([dict(email='text1@test.com', name='文字校对', password='t12345')])
        self.assert_code(200, self.login(user1[0], user1[1]))
        r = self.parse_response(self.fetch('/my/profile'))
        self.assertIn(user1[0], r)
