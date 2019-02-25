#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""
from tests.testcase import APITestCase
import controller.errors as e
import model.user as u

user1 = 'text1@test.com', 't12345'
user2 = 'text2@test.com', 't12312'


class TestTextTask(APITestCase):
    def setUp(self):
        super(APITestCase, self).setUp()
        self.add_users([dict(email=user1[0], name='文字测试', password=user1[1]),
                        dict(email=user2[0], name='测试文字', password=user2[1])], u.ACCESS_TEXT_PROOF)

    def tearDown(self):
        
        # 退回所有任务
        self.login_as_admin()
        self.fetch('/api/unlock/text1_proof/')
        
        super(APITestCase, self).setUp()

    def test_get_tasks_no_open(self):
        """ 测试默认未发布任务时文字校对任务取不到 """
        
        r = self.login(user1[0], user1[1])
        if self.get_code(r) == 200:
            r = self.parse_response(self.fetch('/dzj_chars?_raw=1&count=1'))
            self.assertIn('tasks', r)
            self.assertEqual(len(r['tasks']), 0)

    def test_get_tasks(self):
        """ 测试文字校对任务的发布、列表和领取 """

        # 发布任务
        self.login_as_admin()
        r = self.fetch('/api/start/', body=dict(data=dict(types='text1_proof')))
        self.assertIn('names', self.parse_response(r))

        r = self.login(user1[0], user1[1])
        if self.get_code(r) == 200:
            # 取任务列表
            r = self.parse_response(self.fetch('/dzj_chars?_raw=1&count=1'))
            self.assertIn('tasks', r)
            self.assertEqual(len(r['tasks']), 1)
            name = r['tasks'][0].get('name')
            self.assertTrue(r['tasks'][0].get('name'))

            # 领取任务
            r = self.fetch('/api/pick/text1_proof/' + name)
            self.assertIn('name', self.parse_response(r))

            # 在下次任务列表中未提交的页面将显示在上面
            r = self.parse_response(self.fetch('/dzj_chars?_raw=1&count=99999'))
            self.assertEqual('待继续', r['tasks'][0].get('status'))
            self.assertNotEqual(r['tasks'][-1]['name'], name)

            # 可以继续上次未完成的任务
            self.assertIn('name', self.parse_response(self.fetch('/api/pick/text1_proof/' + name)))

            # 未完成时不能领取新的任务
            r = self.fetch('/api/pick/text1_proof/' + r['tasks'][-1].get('name'))
            self.assert_code(e.task_uncompleted, r)

            self.login(user2[0], user2[1])

            # 其他人不能领取相同任务
            r = self.fetch('/api/pick/text1_proof/' + name)
            self.assert_code(e.task_locked, r)

            # 其他人在下次任务列表中看不到此页面
            r = self.parse_response(self.fetch('/dzj_chars?_raw=1&count=99999'))
            self.assertEqual(r.get('remain'), len(r['tasks']))
            self.assertNotIn(name, [t['name'] for t in r['tasks']])
