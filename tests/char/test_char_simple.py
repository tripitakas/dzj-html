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
        self.delete_tasks_and_locks()

    def tearDown(self):
        super(TestCharTask, self).tearDown()

    def test_publish_char_task(self):
        # 测试发布聚类校对任务
        self._app.db.char.update_many({}, {'$set': {'source': '测试'}})
        data = {'batch': '22TestPages', 'task_type': 'cluster_proof', 'source': '测试', 'num': 1}
        r = self.fetch('/api/char/publish_task', body={'data': data})
        self.assert_code(200, r)

        # 测试不能重复发布同一校次的任务
        data = {'batch': '22TestPages', 'task_type': 'cluster_proof', 'source': '测试', 'num': 1}
        d = self.parse_response(self.fetch('/api/char/publish_task', body={'data': data}))
        self.assertNotEqual(d.get('published'), [])

        # 测试可以发布不同校次的任务
        data = {'batch': '22TestPages', 'task_type': 'cluster_proof', 'source': '测试', 'num': 2}
        d = self.parse_response(self.fetch('/api/char/publish_task', body={'data': data}))
        self.assertEqual(d.get('published'), [])

    def test_update_char(self):
        char1 = self._app.db.char.find_one({})

        # 测试专家一可以修改单字
        self.login(u.expert1[0], u.expert1[1])
        data = {'txt': '测', 'edit_type': 'char_edit'}
        r = self.fetch('/api/char/%s' % char1['_id'], body={'data': data})
        self.assert_code(200, r)

        # 测试数据等级已经修改
        char1 = self._app.db.char.find_one({'_id': char1['_id']})
        self.assertIsNotNone(char1.get('data_level'))

        # 测试专家二修改时，提示等级不够
        self.login(u.expert2[0], u.expert2[1])
        data = {'txt': '测', 'edit_type': 'char_edit'}
        r = self.fetch('/api/char/%s' % char1['_id'], body={'data': data})
        self.assert_code(e.data_level_unqualified[0], r)

        # 测试专家一可以修改自己刚刚改过的字
        self.login(u.expert1[0], u.expert1[1])
        data = {'txt': '试', 'edit_type': 'char_edit'}
        r = self.fetch('/api/char/%s' % char1['_id'], body={'data': data})
        self.assert_code(200, r)
