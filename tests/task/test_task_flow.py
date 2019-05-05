#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase
from controller.role import assignable_do_roles
import controller.errors as e

user1 = 'expert1@test.com', 't12345'
user2 = 'expert2@test.com', 't12312'
user3 = 'expert3@test.com', 't12312'


class TestTaskFlow(APITestCase):
    def setUp(self):
        super(APITestCase, self).setUp()

        # 创建几个专家用户（权限足够），用于审校流程的测试
        admin = self.add_users([dict(email=r[0], name='专家%s' % '一二三'[i], password=r[1])
                                for i, r in enumerate([user1, user2, user3])],
                               ','.join(['切分专家', '文字专家']))
        self.assert_code([200, e.no_change],
                         self.fetch('/api/user/role', body={'data': dict(_id=admin['_id'],
                                                                         roles='用户管理员,任务管理员')}))

    def tearDown(self):
        # 退回所有任务，还原改动
        for task_type in assignable_do_roles:
            self.assert_code(200, self.fetch('/api/unlock/%s/' % task_type))

        super(APITestCase, self).setUp()

    def publish(self, task_type, data):
        return self.fetch('/api/task/publish/%s' % task_type, body={'data': data})

    def test_publish_tasks(self):
        """ 在页面创建后，通过界面和接口发布审校任务 """

        # 通过API发布栏切分校对任务（栏切分没有前置任务，简单）
        self.login_as_admin()
        r = self.parse_response(self.publish('block_cut_proof', dict(pages='')))
        self.assertIsInstance(r, list)
        self.assertEqual(r, [])
        r = self.parse_response(self.publish('block_cut_proof',
                                             dict(pages='GL_1056_5_6,JX_165_7_12', priority='高')))
        self.assertEqual(['GL_1056_5_6', 'JX_165_7_12'], [t['name'] for t in r])
        self.assertEqual({'opened'}, set([t['status'] for t in r]))

        # 再发布有前置任务的栏切分审定任务，将跳过不存在的页面
        r = self.parse_response(self.publish('block_cut_review',
                                             dict(pages='GL_1056_5_6,JX_165_7_30,JX_er', priority='中')))
        self.assertEqual(['GL_1056_5_6', 'JX_165_7_30'], [t['name'] for t in r])
        self.assertEqual(['pending', 'opened'], [t['status'] for t in r])

        # 测试有子任务类型的情况
        r = self.parse_response(self.publish('text_proof.1', dict(pages='GL_1056_5_6,JX_165_7_30')))
        self.assertEqual(['GL_1056_5_6', 'JX_165_7_30'], [t['name'] for t in r])
        self.assertEqual(['opened', 'opened'], [t['status'] for t in r])
        r = self.parse_response(self.publish('text_proof.2', dict(pages='GL_1056_5_6,JX_165_7_30')))
        self.assertEqual(['opened', 'opened'], [t['status'] for t in r])

        r = self.parse_response(self.publish('text_review', dict(pages='GL_1056_5_6')))
        self.assertEqual(['GL_1056_5_6'], [t['name'] for t in r])
        self.assertEqual(['pending'], [t['status'] for t in r])

    def test_task_lobby(self):
        """ 测试任务大厅 """

        self.login_as_admin()
        for task_type in ['block_cut_proof', 'column_cut_proof', 'char_cut_proof', 'block_cut_review',
                          'column_cut_review', 'char_cut_review', 'text_proof', 'text_review']:
            if task_type == 'text_proof':
                for i in range(1, 4):
                    r = self.parse_response(self.publish('%s.%d' % (task_type, i), dict(pages='GL_1056_5_6,JX_165_7_12')))
            else:
                r = self.parse_response(self.publish(task_type, dict(pages='GL_1056_5_6,JX_165_7_12')))
            self.assertEqual({'opened'}, set([t['status'] for t in r]), msg=task_type)

            r = self.fetch('/task/lobby/%s?_raw=1&_no_auth=1' % task_type)
            self.assert_code(200, r, msg=task_type)
            r = self.parse_response(r)
            self.assertEqual(['GL_1056_5_6', 'JX_165_7_12'], [t['name'] for t in r['tasks']], msg=task_type)
            self.assert_code(200, self.fetch('/api/unlock/cut/'))
            self.assert_code(200, self.fetch('/api/unlock/text/'))
