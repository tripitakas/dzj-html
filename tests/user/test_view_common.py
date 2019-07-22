#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/6/12
"""
import tests.users as u
from tests.testcase import APITestCase


class TestUserCommonViews(APITestCase):
    def setUp(self):
        super(TestUserCommonViews, self).setUp()

    def test_view_login(self):
        """测试登录页面"""
        r = self.fetch('/user/login')
        data = self.parse_response(r)
        self.assert_code(200, r)
        self.assertIn('<!DOCTYPE html>', data)

    def test_view_register(self):
        """测试注册页面"""
        r = self.fetch('/user/register')
        data = self.parse_response(r)
        self.assert_code(200, r)
        self.assertIn('<!DOCTYPE html>', data)

    def test_view_home(self):
        """测试首页"""
        self.add_first_user_as_admin_then_login()
        r = self.fetch('/')
        data = self.parse_response(r)
        self.assert_code(200, r)
        self.assertIn('<!DOCTYPE html>', data)

    def test_view_profile(self):
        """测试个人中心"""
        # 管理员
        self.add_first_user_as_admin_then_login()
        r = self.fetch('/user/my/profile')
        self.assert_code(200, r)
        data = self.parse_response(r)
        self.assertIn(u.admin[0], data)
        # 普通用户
        r = self.register_and_login(dict(email=u.user1[0], password=u.user1[1], name=u.user1[2]))
        self.assert_code(200, r)
        r = self.fetch('/user/my/profile')
        self.assert_code(200, r)
        data = self.parse_response(r)
        self.assertIn(u.user1[0], data)

    def test_view_404(self):
        """测试不存在的页面"""
        self.assert_code(404, self.fetch('/xyz'))

    def test_view_show_api(self):
        r = self.parse_response(self.fetch('/api?_raw=1'))
        self.assertIn('handlers', r)
        for url, func, repeat, file, comment, auth in r['handlers']:
            # 控制器类的get/post方法需要写简要的文档字符串
            self.assertNotIn(comment, ['', 'None', None], '%s %s need doc comment' % (url, func))

            r2 = self.fetch('/api/code/%s?_raw=1' % (func,))
            self.assertEqual(self.parse_response(r2).get('name'), func)
