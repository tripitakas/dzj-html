#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/05/07
"""
import tests.users as u
import controller.errors as e
from tests.testcase import APITestCase


class TestUserAdminApi(APITestCase):
    def setUp(self):
        super(TestUserAdminApi, self).setUp()
        self.add_first_user_as_admin_then_login()

    def test_user_admin_roles(self):
        """ 给用户授予角色 """
        users = self.add_users_by_admin([dict(email=u.user1[0], password=u.user1[1], name=u.user1[2])])
        r = self.fetch('/api/user/roles', body={'data': dict(_id=users[0]['_id'], email=u.user1[0], roles='切分校对员')})
        self.assert_code(200, r)
        data = self.parse_response(r)
        self.assertIn('切分校对员', data['roles'])

    def test_user_admin_reset_password(self):
        """ 重置用户密码 """
        users = self.add_users_by_admin([dict(email=u.user1[0], password=u.user1[1], name=u.user1[2])])
        r = self.fetch('/api/user/admin/reset_pwd', body={'data': dict(_id=users[0]['_id'])})
        self.assert_code(200, r)
        data = self.parse_response(r)
        self.assertIsNotNone(data['password'])

    def test_user_admin_change_profile(self):
        """ 修改用户profile """
        users = self.add_users_by_admin([dict(email=u.user1[0], password=u.user1[1], name=u.user1[2])])
        user1 = users[0]
        self.add_users_by_admin([dict(email=u.user2[0], password=u.user2[1], name=u.user2[2])])

        # 邮箱不能重复
        body = {'data': dict(_id=user1['_id'], name=user1['name'], email=u.user2[0], phone=user1.get('phone'))}
        r = self.fetch('/api/user/admin', body=body)
        self.assert_code(e.doc_existed, r)

        # 邮箱格式有误
        data = dict(_id=user1['_id'], name=user1['name'], email='123#123', phone=user1.get('phone'))
        r = self.fetch('/api/user/admin', body={'data': data})
        self.assert_code(e.invalid_email, r)

        # 正常修改
        data = dict(_id=user1['_id'], name=user1['name'], email='user1_new@test.com', phone=user1.get('phone'))
        r = self.fetch('/api/user/admin', body={'data': data})
        self.assert_code(200, r)

    def test_user_admin_delete_user(self):
        """ 测试删除用户 """
        users = self.add_users_by_admin([dict(email=u.user1[0], password=u.user1[1], name=u.user1[2])])
        r = self.fetch('/api/user/admin/delete', body={'data': dict(_id=users[0]['_id'])})
        self.assert_code(200, r)
