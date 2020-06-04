#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.users as u
from controller import errors as e
from tests.testcase import APITestCase
from tornado.escape import json_encode


class TestCharTask(APITestCase):
    def setUp(self):
        super(TestCharTask, self).setUp()
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3, u.expert3]],
            '切分专家,文字专家,聚类校对员,聚类审定员'
        )
        self.reset_tasks_and_data()

    def tearDown(self):
        super(TestCharTask, self).tearDown()

    def test_publish_char_task(self):
        """ 测试发布聚类校对任务"""
        # 设置分类
        self._app.db.char.update_many({}, {'$set': {'source': '测试数据'}})
        data = {'source': '测试数据', 'batch': '测试任务', 'task_type': 'cluster_proof', 'num': 1}
        r = self.fetch('/api/char/task/publish', body={'data': data})
        self.assert_code(200, r)

        # 测试不能重复发布同一校次的任务
        data = {'source': '测试数据', 'batch': '测试任务', 'task_type': 'cluster_proof', 'num': 1}
        d = self.parse_response(self.fetch('/api/char/task/publish', body={'data': data}))
        self.assertNotEqual(d.get('published'), [])

        # 测试可以发布不同校次的任务
        data = {'source': '测试数据', 'batch': '测试任务', 'task_type': 'cluster_proof', 'num': 2}
        d = self.parse_response(self.fetch('/api/char/task/publish', body={'data': data}))
        self.assertEqual(d.get('published'), [])
