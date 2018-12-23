#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Zhang Yungui
@time: 2018/6/12
"""
import controller.errors as e
from tests.testcase import APITestCase

admin = 'admin@test.com', 'test123'


class TestUserApi(APITestCase):

    def test_login_invalid(self):
        """ 测试接口可工作 """
        response = self.fetch('/api/user/login', body={})
        self.assert_code(500, response)

        response = self.fetch('/api/user/login', body={'data': dict(email='')})
        self.assert_code(e.need_email, response)

        response = self.fetch('/api/user/login', body={'data': dict(email='test')})
        self.assert_code(e.need_password, response)

    def test_register(self):
        """ 测试注册和登录，测试第一个用户为管理员 """
        r = self.fetch('/api/user/register', body={'data': dict(email=admin[0], name='管理', password=admin[1])})
        r = self.parse_response(r)
        if 'error' not in r:
            self.assertIn('超级管理员', r['authority'])
        else:
            r = self.fetch('/api/user/login', body={'data': dict(email=admin[0], password='test')})
            self.assert_code(e.invalid_password, r)
            r = self.fetch('/api/user/login', body={'data': dict(email=admin[0], password=admin[1])})
            self.assert_code(200, r)

    def test_assign_authority(self):
        """ 测试为新用户设置权限 """

        # 注册一个新用户
        self.fetch('/api/user/register', body={'data': dict(email='t1@test.com', name='测试', password='t12345')})
        r = self.fetch('/api/user/login', body={'data': dict(email='t1@test.com', password='t12345')})
        user = self.parse_response(r)
        self.assertIn('id', user)

        # 普通用户无权设置权限
        r = self.fetch('/api/user/change', body={'data': dict(
            id=user['id'], email=user['email'], authority='切分校对员')})
        self.assert_code(e.unauthorized, r)

        # 管理员可设置或取消权限
        r = self.fetch('/api/user/login', body={'data': dict(email=admin[0], password=admin[1])})
        self.assert_code(200, r)
        r = self.fetch('/api/user/change', body={'data': dict(
            id=user['id'], email=user['email'], authority='切分校对员')})
        self.assert_code([200, e.no_change], r)
        self.fetch('/api/user/change', body={'data': dict(id=user['id'], email=user['email'], authority='')})
