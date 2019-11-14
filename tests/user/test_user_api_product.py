#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/6/12
"""
import tests.users as u
import controller.errors as e
from controller.helper import prop
from tests.testcase import APITestCase


class TestUserProductApi(APITestCase):

    # def get_app(self, testing=False, debug=False):
    #     return super(TestUserProductApi, self).get_app(testing=testing, debug=debug)

    def setUp(self):
        super(TestUserProductApi, self).setUp()

    def test_api_send_email_code(self):
        account = prop(self._app.config, 'email.account')
        if account and '待配置' not in account:
            email = 'lqs.xiandu@qq.com'
            d = self._app.db.user.delete_one(dict(email=email))
            if d:
                r = self.fetch('/api/user/email_code', body={'data': dict(email=email)})
                self.assert_code(200, r)
                # 测试验证码错误时的结果
                r = self.fetch('/api/user/register', body={
                    'data': dict(email=email, password=u.user1[1], name=u.user1[2], email_code='jskl')
                })
                self.assert_code(e.code_wrong_or_timeout, r)
            # 测试验证码正确时的结果
            verify = self._app.db.verify.find_one(dict(type='email', data=email))
            if verify:
                code = verify.get('code')
                r = self.fetch('/api/user/register', body={
                    'data': dict(email=email, password=u.user1[1], name=u.user1[2], email_code=code)
                })
                self.assert_code(200, r)

    def test_api_send_phone_code(self):
        account = prop(self._app.config, 'phone.accessKey')
        if account and '待配置' not in account:
            phone = '13810916830'
            d = self._app.db.user.delete_one(dict(phone=phone))
            if d:
                r = self.fetch('/api/user/phone_code', body={'data': dict(phone=phone)})
                self.assert_code(200, r)
                # 测试验证码错误时的结果
                r = self.fetch('/api/user/register', body={
                    'data': dict(phone=phone, password=u.user1[1], name=u.user1[2], phone_code='3564')
                })
                self.assert_code(e.code_wrong_or_timeout, r)
            # 测试验证码正确时的结果
            verify = self._app.db.verify.find_one(dict(type='phone', data=phone))
            if verify:
                code = verify.get('code')
                r = self.fetch('/api/user/register', body={
                    'data': dict(phone=phone, password=u.user1[1], name=u.user1[2], phone_code=code)
                })
                self.assert_code(200, r)
