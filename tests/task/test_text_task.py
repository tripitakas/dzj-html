#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Zhang Yungui
@time: 2018/12/27
"""
from tests.testcase import APITestCase
import controller.errors as e

admin = 'admin@test.com', 'test123'
user1 = 'text1@test.com', 't12345'
user2 = 'text2@test.com', 't12312'


class TestTextTask(APITestCase):
    created = False

    def setUp(self):
        super(APITestCase, self).setUp()

        self.add_admin_user()
        self.fetch('/api/user/register', body={'data': dict(email=user1[0], name='文字测试', password=user1[1])})
        self.fetch('/api/user/register', body={'data': dict(email=user2[0], name='测试文字', password=user2[1])})

        self.fetch('/api/user/login', body={'data': dict(email=admin[0], password=admin[1])})
        r1 = self.fetch('/api/user/change', body={'data': dict(email=user1[0], authority='文字校对员')})
        r2 = self.fetch('/api/user/change', body={'data': dict(email=user2[0], authority='文字校对员')})
        self.created = self.get_code(r1) in [200, e.no_change[0]] and self.get_code(r2) in [200, e.no_change[0]]

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
            r = self.fetch('/api/pick/text/' + name)
            self.assertIn('name', self.parse_response(r))

            # 在下次任务列表中未提交的页面将显示在上面
            r = self.parse_response(self.fetch('/dzj_chars?_raw=1&count=99999'))
            self.assertEqual('待继续', r['tasks'][0].get('status'))
            self.assertNotEqual(r['tasks'][-1]['name'], name)

            # 未完成时不能领取新的任务
            r = self.fetch('/api/pick/text/' + r['tasks'][-1].get('name'))
            self.assert_code(e.task_uncompleted, r)

            self.fetch('/api/user/login', body={'data': dict(email=user2[0], password=user2[1])})

            # 其他人不能领取相同任务
            r = self.fetch('/api/pick/text/' + name)
            self.assert_code(e.task_locked, r)

            # 其他人在下次任务列表中看不到此页面
            r = self.parse_response(self.fetch('/dzj_chars?_raw=1&count=99999'))
            self.assertEqual(r.get('remain'), len(r['tasks']))
            self.assertNotIn(name, [t['name'] for t in r['tasks']])
