#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/6/12
"""
import controller.errors as e
from tests.testcase import APITestCase
import tests.users as u


class TestUserCommonApi(APITestCase):
    def setUp(self):
        super(TestUserCommonApi, self).setUp()

    def test_api_404(self):
        """不存在的API接口"""
        r = self.fetch('/api/xyz')
        rs = self.parse_response(r)
        self.assert_code(404, r)
        self.assertFalse(rs)

    def test_api_login(self):
        """ 登录api """
        # 测试接口有效性
        r = self.fetch('/api/user/login', body={'data': dict(phone_or_email='')})
        self.assert_code(e.not_allowed_empty, r)

        # 测试管理员用户
        self.add_first_user_as_admin_then_login()
        r = self.fetch('/api/user/login', body={'data': dict(phone_or_email=u.admin[0], password='')})
        self.assert_code([e.need_password, e.not_allowed_empty], r)
        r = self.fetch('/api/user/login', body={'data': dict(phone_or_email=u.admin[0], password=u.admin[1])})
        self.assert_code(200, r)
        data = self.parse_response(r)
        self.assertIn('用户管理员', data['roles'])

        # 测试普通用户
        self.add_users_by_admin([dict(email=u.user1[0], password=u.user1[1], name=u.user1[2])])
        r = self.fetch('/api/user/login', body={'data': dict(phone_or_email=u.user1[0], password=u.user1[1])})
        self.assert_code(200, r)

    def test_api_change_my_pwd(self):
        """修改个人密码"""
        pass

    def test_api_change_my_profile(self):
        """修改个人信息"""
        pass