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
user3 = 'cut_text@test.com', 't12312'


class TestTextTask(APITestCase):
    def setUp(self):
        super(APITestCase, self).setUp()
        self.add_users([dict(email=user1[0], name='文字测试', password=user1[1]),
                        dict(email=user3[0], name='切分文字', password=user3[1],
                             auth=','.join([u.ACCESS_TEXT_PROOF + u.ACCESS_CUT_PROOF])),
                        dict(email=user2[0], name='测试文字', password=user2[1])], u.ACCESS_TEXT_PROOF)

    def tearDown(self):
        
        # 退回所有任务
        self.login_as_admin()
        self.fetch('/api/unlock/cut_proof/')
        self.fetch('/api/unlock/text1_proof/')
        
        super(APITestCase, self).setUp()

    def test_get_tasks_no_open(self):
        """ 测试默认未发布任务时文字校对任务取不到 """
        
        r = self.login(user1[0], user1[1])
        if self.get_code(r) == 200:
            r = self.parse_response(self.fetch('/dzj_chars?_raw=1&count=1'))
            self.assertIn('tasks', r)
            self.assertEqual(len(r['tasks']), 0)

    def start_tasks(self, types, prefix='', priority='高'):
        return self.fetch('/api/start/' + prefix, body={'data': dict(types=types, priority=priority)})

    def test_get_tasks(self):
        """ 测试文字校对任务的发布、列表和领取 """

        # 发布任务
        self.login_as_admin()
        r = self.start_tasks('text1_proof')
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

    def test_multi_stages(self):
        """ 测试校、审任务的状态转换 """

        # 同时发布一个藏别的切分校对任务和文字校对任务
        self.login_as_admin()
        self.fetch('/api/unlock/cut_proof/')
        r = self.start_tasks('text1_proof,char_cut_proof', 'JX')
        r = self.parse_response(r)
        self.assertGreater(len(r['names']), 1)
        self.assertEqual(len(r['names']) * 2, len(r['items']))
        self.assertEqual(r['items'][0]['status'], u.STATUS_OPENED)
        self.assertEqual(r['items'][1]['status'], u.STATUS_PENDING)
        name = r['items'][0]['name']

        # 依赖前面任务的任务不能领取，要具有相应权限
        self.login(user1[0], user1[1])
        self.assert_code(e.task_locked, self.fetch('/api/pick/text1_proof/' + name))
        self.assert_code(e.unauthorized, self.fetch('/api/pick/char_cut_proof/' + name))
        self.login(user3[0], user3[1])
        self.assert_code(200, self.fetch('/api/pick/char_cut_proof/' + name))

        # 进入切分校对页面
        r = self.fetch('/dzj_char_cut_proof/%s?_raw=1' % name)
        self.assert_code(200, r)
        page = self.parse_response(r)['page']
        self.assertEqual(page['name'], name)

        # 任务提交后自动流转到下一校次
        # TODO

    def test_pages_start_fetch(self):
        """ 测试任务发布和获取页名 """

        # 准备发布任务，得到页名
        r = self.parse_response(self.fetch('/api/pages/cut_start', body={}))
        self.assertIn('items', r)
        self.assertIsInstance(r['items'][0], str)
        names = r['items']

        # 先发布一种任务类型
        self.login_as_admin()
        r = self.start_tasks('char_cut_proof')
        self.assert_code(200, r)
        for p in self.parse_response(r)['items']:
            self.assertEqual(p.get('task_type'), 'char_cut_proof')
            self.assertEqual(p.get('status'), u.STATUS_OPENED)

        # 因为还有其他任务类型，所以得到的页名没少
        r = self.parse_response(self.fetch('/api/pages/cut_start', body={}))
        self.assertEqual(len(r['items']), len(names))

        # 如果取同一类型则没有空闲页名了
        r = self.parse_response(self.fetch('/api/pages/cut_start', body={'data': dict(types='char_cut_proof')}))
        self.assertEqual(len(r['items']), 0)
        # 也不能再发布同一类型的任务了
        r = self.parse_response(self.start_tasks('char_cut_proof'))
        self.assertEqual(len(r['items']), 0)

        # 还可以发布其他类型的任务
        r = self.parse_response(self.fetch('/api/pages/cut_start', body={'data': dict(types='column_cut_proof')}))
        self.assertIn('items', r)
        self.assertEqual(len(r['items']), len(names))

    def test_precondition_tasks(self):
        """ 测试分批发布不同类型的任务时依依赖任务而为未就绪 """

        r = self.parse_response(self.start_tasks('block_cut_proof,char_cut_proof', priority='中'))
        names, items = r['names'], r['items']
        self.assertEqual(len(names) * 2, len(r['items']))

        r = self.parse_response(self.fetch('/api/page/' + names[0]))
        self.assertEqual(r.get('char_cut_proof_priority'), '中')

        r = self.parse_response(self.start_tasks('column_cut_proof'))
        self.assertEqual(len(names), len(r['names']))
        self.assertEqual(r['items'][0].get('status'), u.STATUS_PENDING)
