#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/6/12
"""
import controller.errors as e
from tests.testcase import APITestCase

admin = 'admin@test.com', 'test123'


class TestUserApi(APITestCase):

    def test_login_invalid(self):
        """ 测试接口可工作 """
        response = self.fetch('/api/user/login', body={'data': dict(email='')})
        self.assert_code(e.need_phone_or_email, response)

        response = self.fetch('/api/user/login', body={'data': dict(email='test')})
        self.assert_code(e.need_password, response)

    def _register_login(self, info):
        return self.fetch('/api/user/register', body={'data': info})

    def test_register(self):
        """ 测试注册和登录，测试第一个用户为管理员 """
        r = self.add_admin_user()
        r = self.parse_response(r)
        if 'error' not in r:
            self.assertIn('用户管理员', r['roles'])
        else:
            r = self.fetch('/api/user/login', body={'data': dict(email=admin[0], password='test')})
            self.assert_code(e.incorrect_password, r)
            r = self.fetch('/api/user/login', body={'data': dict(email=admin[0], password=admin[1])})
            self.assert_code(200, r)
            self.assertIn('user_admin', self.parse_response(r).get('roles'))

    def test_assign_roles(self):
        """ 测试为新用户设置权限 """

        # 注册一个新用户
        self.add_admin_user()
        r = self._register_login(dict(email='t1@test.com', name='测试', password='t12345'))
        user = self.parse_response(r)
        self.assertIn('id', user)

        # 普通用户无权设置权限
        r = self.fetch('/api/user/role', body={'data': dict(
            id=user['id'], email=user['email'], roles='切分校对员')})
        self.assert_code([e.unauthorized, e.no_change], r)

        # 可以修改自己的基本信息
        r = self.fetch('/api/my/profile', body={'data': dict(
            id=user['id'], email=user['email'], name='教师甲')})
        self.assert_code(200, r)
        r = self.fetch('/api/user/profile', body={'data': dict(
            id=user['id'], email=user['email'], name='教师甲')})
        self.assert_code(e.unauthorized, r)

        # 普通用户取用户列表只能得到自己
        '''
        r = self.parse_response(self.fetch('/api/user/list?_no_auth=1'))
        self.assertEqual(len(r.get('items', [])), 1)
        self.assertIn('教师甲', [t['name'] for t in r.get('items', [])])
        '''

        # 管理员可设置或取消权限
        r = self.fetch('/api/user/login', body={'data': dict(email=admin[0], password=admin[1])})
        self.assert_code(200, r)
        r = self.fetch('/api/user/role', body={'data': dict(
            id=user['id'], email=user['email'], roles='切分校对员')})
        self.assert_code([200, e.no_change], r)
        self.fetch('/api/user/role', body={'data': dict(id=user['id'], email=user['email'], roles='')})

    def test_change_password(self):
        """ 测试修改密码、重置密码、删除用户 """

        self.assert_code(200, self.add_admin_user())
        self.fetch('/api/user/remove', body={'data': dict(email='t2@test.com', name='测试')})
        r = self._register_login(dict(email='t2@test.com', name='测试', password='t12345'))
        user = self.parse_response(r)

        # 修改密码
        r = self.fetch('/api/my/pwd', body={'data': dict(old_password='err123', password='test123')})
        self.assert_code(e.incorrect_password, r)
        r = self.fetch('/api/my/pwd', body={'data': dict(old_password='t12345', password='test123')})
        self.assert_code(200, r)

        r = self.fetch('/api/user/logout')
        self.assert_code(200, r)

        self.fetch('/api/user/login', body={'data': dict(email=admin[0], password=admin[1])})

        # 管理员为其重置密码
        r = self.fetch('/api/user/reset_pwd', body={'data': dict(id=user['id'])})
        result = self.parse_response(r)
        self.assertIn('password', result)

        # 修改用户信息
        r = self.fetch('/api/user/profile', body={'data': dict(id=user['id'], gender='男')})
        result = self.parse_response(r)
        self.assertTrue(result.get('info'))

        # 删除用户后不能再登录
        r = self.fetch('/api/user/remove', body={'data': dict(email='t2@test.com', name='测试')})
        self.assert_code(200, r)
        r = self.fetch('/api/user/login', body={'data': dict(email='t2@test.com', password='t12345')})
        self.assert_code(e.no_user, r)
