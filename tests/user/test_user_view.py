#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/05/07
"""
import tests.users as u
from tests.testcase import APITestCase


class TestUserViews(APITestCase):
    def setUp(self):
        super(TestUserViews, self).setUp()

    def test_user_view_login(self):
        """测试登录页面"""
        r = self.fetch('/user/login')
        data = self.parse_response(r)
        self.assert_code(200, r)
        self.assertIn('<!DOCTYPE html>', data)

    def test_user_view_register(self):
        """测试注册页面"""
        r = self.fetch('/user/register')
        data = self.parse_response(r)
        self.assert_code(200, r)
        self.assertIn('<!DOCTYPE html>', data)

    def test_user_view_home(self):
        """测试首页"""
        self.add_first_user_as_admin_then_login()
        r = self.fetch('/')
        data = self.parse_response(r)
        self.assert_code(200, r)
        self.assertIn('<!DOCTYPE html>', data)

    def test_user_view_profile(self):
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

    def test_user_view_admin(self):
        """ 用户管理页面"""
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin([dict(email=u.user1[0], password=u.user1[1], name=u.user1[2])])
        r = self.fetch('/user/admin')
        self.assert_code(200, r)
        data = self.parse_response(r)
        self.assertIn(u.user1[0], data)

    def test_user_view_role(self):
        """ 角色管理页面"""
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin([dict(email=u.user1[0], password=u.user1[1], name=u.user1[2])])
        r = self.fetch('/user/role')
        self.assert_code(200, r)
        data = self.parse_response(r)
        self.assertIn(u.user1[0], data)
