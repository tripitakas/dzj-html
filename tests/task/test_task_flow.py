#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase
import controller.errors as e
import model.user as u

user1 = 'expert1@test.com', 't12345'
user2 = 'expert2@test.com', 't12312'
user3 = 'expert3@test.com', 't12312'


class TestTaskFlow(APITestCase):
    def setUp(self):
        super(APITestCase, self).setUp()

        # 创建几个专家用户（权限足够），用于审校流程的测试
        self.add_users([dict(email=r[0], name='专家%s' % '一二三'[i], password=r[1])
                        for i, r in enumerate([user1, user2, user3])],
                       ','.join([u.ACCESS_CUT_EXPERT, u.ACCESS_TEXT_EXPERT]))

    def tearDown(self):
        # 退回所有任务，还原改动
        self.login_as_admin()
        self.assert_code(200, self.fetch('/api/unlock/cut/'))
        self.assert_code(200, self.fetch('/api/unlock/text/'))

        super(APITestCase, self).setUp()

    def publish(self, task_type, data):
        return self.fetch('/api/task/publish/' + task_type, body={'data': data})

    def test_publish_tasks(self):
        """ 在页面创建后，通过界面和接口发布审校任务 """

        # 通过API发布栏切分校对任务（栏切分没有前置任务，简单）
        self.login_as_admin()
        r = self.parse_response(self.publish('block_cut_proof', dict(pages='')))
        self.assertIsInstance(r.get('items'), list)
        self.assertEqual(r['items'], [])
        r = self.parse_response(self.publish('block_cut_proof',
                                             dict(pages='GL_1056_5_6,JX_165_7_12', priority='高')))
        self.assertEqual(['GL_1056_5_6', 'JX_165_7_12'], [t['name'] for t in r['items']])
        self.assertEqual({'opened'}, set([t['status'] for t in r['items']]))

        # 再发布有前置任务的栏切分审定任务，将跳过不存在的页面
        r = self.parse_response(self.publish('block_cut_review',
                                             dict(pages='GL_1056_5_6,JX_165_7_30,JX_err', priority='中')))
        self.assertEqual(['GL_1056_5_6', 'JX_165_7_30'], [t['name'] for t in r['items']])
        self.assertEqual(['pending', 'pending'], [t['status'] for t in r['items']])
