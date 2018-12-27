#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Zhang Yungui
@time: 2018/12/27
"""
from tests.testcase import APITestCase
import controller.errors as e

admin = 'admin@test.com', 'test123'
user1 = 'text@test.com', 't12345'


class TestTextTask(APITestCase):
    created = False

    def setUp(self):
        super(APITestCase, self).setUp()
        self.fetch('/api/user/register', body={'data': dict(email=user1[0], name='文字测试', password=user1[1])})

        self.fetch('/api/user/login', body={'data': dict(email=admin[0], password=admin[1])})
        r = self.fetch('/api/user/change', body={'data': dict(email=user1[0], authority='文字校对员')})
        self.created = self.get_code(r) in [200, e.no_change[0]]

    def test_get_tasks(self):
        r = self.fetch('/api/user/login', body={'data': dict(email=user1[0], password=user1[1])})
        if self.get_code(r) == 200 and self.created:
            r = self.fetch('/api/pick/text/JX_165_7_12')
            self.assert_code(200, r)
