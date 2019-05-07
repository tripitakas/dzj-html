#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/05/07
"""
import controller.errors as e
from tests.testcase import APITestCase
import tests.users as u


class TestUserAdminApi(APITestCase):
    def setUp(self):
        super(TestUserAdminApi, self).setUp()

    def _get_user_by_email(self, email):
        return self._app.db.user.find_one(dict(email=email))

    def _get_id_by_email(self, email):
        user = self._app.db.user.find_one(dict(email=email))
        return user.get('_id') if user else None

    def test_api_admin_roles(self):
        """ 给用户授予角色 """
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin([dict(email=u.user1[0], password=u.user1[1], name=u.user1[2])])
        uid = self._get_id_by_email(u.user1[0])
        r = self.fetch('/api/user/role', body={'data': dict(_id=uid, email=u.user1[0], roles='切分校对员')})
        self.assert_code(200, r)
        data = self.parse_response(r)
        self.assertIn('切分校对员', data['roles'])

    def test_api_admin_reset_password(self):
        """ 重置用户密码 """
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin([dict(email=u.user1[0], password=u.user1[1], name=u.user1[2])])
        uid = self._get_id_by_email(u.user1[0])
        r = self.fetch('/api/user/reset_pwd', body={'data': dict(_id=uid)})
        self.assert_code(200, r)
        data = self.parse_response(r)
        self.assertIsNotNone(data['password'])

    def test_api_admin_change_profile(self):
        """ 修改用户profile """
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin([dict(email=u.user1[0], password=u.user1[1], name=u.user1[2])])
        user1 = self._get_user_by_email(u.user1[0])
        self.assertIsNotNone(user1)
        self.add_users_by_admin([dict(email=u.user2[0], password=u.user2[1], name=u.user2[2])])

        # 邮箱不能重复
        body = {'data': dict(_id=user1['_id'], name=user1['name'], email=u.user2[0], phone=user1['phone'])}
        r = self.fetch('/api/user/profile', body=body)
        self.assert_code(e.record_existed, r)

        # 邮箱格式有误
        r = self.fetch('/api/user/profile', body={
            'data': dict(_id=user1['_id'], name=user1['name'], email='123#123', phone=user1['phone'])
        })
        self.assert_code(e.invalid_email, r)

        # 正常修改
        r = self.fetch('/api/user/profile', body={
            'data': dict(_id=user1['_id'], name=user1['name'], email='user1_new@test.com', phone=user1['phone'])
        })
        self.assert_code(200, r)


