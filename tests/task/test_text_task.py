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

        self.add_admin_user()
        self.fetch('/api/user/register', body={'data': dict(email=user1[0], name='文字测试', password=user1[1])})

        self.fetch('/api/user/login', body={'data': dict(email=admin[0], password=admin[1])})
        r = self.fetch('/api/user/change', body={'data': dict(email=user1[0], authority='文字校对员')})
        self.created = self.get_code(r) in [200, e.no_change[0]]

    def test_get_tasks(self):
        """ 测试文字校对任务的列表和领取 """
        r = self.fetch('/api/user/login', body={'data': dict(email=user1[0], password=user1[1])})
        if self.get_code(r) == 200 and self.created:
            # 取任务列表
            r = self.parse_response(self.fetch('/dzj_chars?_raw=1&count=1'))
            self.assertIn('tasks', r)
            name = len(r.get('tasks', [])) == 1 and r['tasks'][0].get('name')
            self.assertTrue(name)

            # 领取任务
            r = self.fetch('/api/pick/text/' + r['tasks'][0].get('name'))
            self.assertIn('name', self.parse_response(r))

            # 此页面将不出现在下次任务列表中
            r = self.parse_response(self.fetch('/dzj_chars?_raw=1&count=99999'))
            self.assertEqual(r.get('count'), len(r['tasks']))
            self.assertNotIn(name, [t['name'] for t in r['tasks']])
