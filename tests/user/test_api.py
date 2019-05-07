#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/6/12
"""
import controller.errors as e
from tests.testcase import APITestCase, admin


class TestUserApi(APITestCase):
    def setUp(self):
        super(TestUserApi, self).setUp()
        self._app.db.user.drop()

    def test_login_invalid(self):
        """ 测试接口可工作 """
        response = self.fetch('/api/user/login', body={'data': dict(email='')})
        self.assert_code(e.not_allowed_empty, response)

        response = self.fetch('/api/user/login', body={'data': dict(phone_or_email='test')})
        self.assert_code([e.need_password, e.not_allowed_empty], response)

    def test_register(self):
        """ 测试注册和登录，测试第一个用户为管理员 """
        r = self.parse_response(self.add_first_user_as_admin())

        if 'error' not in r:
            self.assertIn('用户管理员', r['roles'])
        else:
            r = self.fetch('/api/user/login', body={'data': dict(phone_or_email=admin[0], password='test')})
            self.assert_code(e.incorrect_password, r)
            r = self.fetch('/api/user/login', body={'data': dict(phone_or_email=admin[0], password=admin[1])})
            self.assert_code(200, r)
            self.assertIn('user_admin', self.parse_response(r).get('roles'))

    def test_assign_roles(self):
        """ 测试为新用户设置权限 """

        # 注册一个新用户
        self.add_first_user_as_admin()
        r = self.register_login(dict(email='t1@test.com', name='测试', password='t12345'))
        user = self.parse_response(r)
        self.assertIn('_id', user)

        # 普通用户无权设置权限
        r = self.fetch('/api/user/role', body={'data': dict(
            _id=user['_id'], email=user['email'], roles='切分校对员')})
        self.assert_code([e.unauthorized, e.no_change], r)

        # 可以修改自己的基本信息
        r = self.fetch('/api/my/profile', body={'data': dict(
            id=user['_id'], email=user['email'], name='教师甲')})
        self.assert_code([200, e.no_change], r)
        r = self.fetch('/api/user/profile', body={'data': dict(
            id=user['_id'], email=user['email'], name='教师甲')})
        self.assert_code(e.unauthorized, r)

        # 管理员可设置或取消权限
        r = self.fetch('/api/user/login', body={'data': dict(phone_or_email=admin[0], password=admin[1])})
        self.assert_code(200, r)
        r = self.fetch('/api/user/role', body={'data': dict(
            _id=user['_id'], email=user['email'], roles='切分校对员')})
        self.assert_code([200, e.no_change], r)
        response = self.parse_response(r)
        self.assertIn('切分校对员', response['roles'])

    def test_change_password(self):
        """ 测试修改密码、重置密码、删除用户 """

        self.add_first_user_as_admin()
        r = self.register_login(dict(email='t3@test.com', name='测试', password='t12345'))
        self.assert_code(200, r)
        user = self.parse_response(r)

        # 修改密码
        r = self.fetch('/api/my/pwd', body={'data': dict(old_password='err123', password='test123')})
        self.assert_code(e.incorrect_old_password, r)
        r = self.fetch('/api/my/pwd', body={'data': dict(old_password='t12345', password='test123')})
        self.assert_code(200, r)

        r = self.fetch('/api/user/logout')
        self.assert_code(200, r)

        self.fetch('/api/user/login', body={'data': dict(phone_or_email=admin[0], password=admin[1])})

        # 管理员为其重置密码
        r = self.fetch('/api/user/reset_pwd', body={'data': dict(_id=user['_id'])})
        result = self.parse_response(r)
        self.assertIn('password', result)
        new_password = result['password']

        # 修改用户信息
        r = self.fetch('/api/user/profile', body={'data': dict(_id=user['_id'], gender='男',
                                                               email=user['email'], name='教师甲')})
        self.assertTrue(self.parse_response(r).get('info') or self.get_code(r) == e.no_change[0])

        if 0:
            # 删除用户后不能再登录
            r = self.fetch('/api/user/remove', body={'data': dict(email='t2@test.com', name='测试')})
            self.assert_code(200, r)
            r = self.fetch('/api/user/login', body={'data': dict(phone_or_email='t2@test.com', password='t12345')})
            self.assert_code(e.no_user, r)
        else:
            # 用新密码登录然后恢复原密码，以便下次测试通过
            r = self.register_login(dict(email='t3@test.com', name='测试', password=new_password))
            self.assert_code(200, r)
            r = self.fetch('/api/my/pwd', body={'data': dict(old_password=new_password, password='t12345')})
            self.assert_code(200, r)
