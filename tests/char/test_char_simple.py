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

    def test_update_char_txt(self):
        """ 测试单字修改"""
        char1 = self._app.db.char.find_one({})

        # 测试专家一可以修改单字
        self.login(u.expert1[0], u.expert1[1])
        txts = [t for t in '测试数据等级' if t != char1['txt']]
        data = {'txt': txts[0], 'txt_type': '', 'is_variant': False, 'task_type': 'cluster_review'}
        r = self.fetch('/api/char/txt/%s' % char1['name'], body={'data': data})
        self.assert_code(200, r)

        # 测试数据等级已经修改
        char1 = self._app.db.char.find_one({'_id': char1['_id']})
        self.assertIsNotNone(char1.get('txt_level'))

        # 测试专家二修改时，提示等级不够
        self.login(u.expert2[0], u.expert2[1])
        data = {'txt': txts[1], 'txt_type': '', 'is_variant': False, 'task_type': 'cluster_proof'}
        r = self.fetch('/api/char/txt/%s' % char1['name'], body={'data': data})
        self.assert_code(e.data_level_unqualified[0], r)

        # 测试专家一可以修改自己刚刚改过的字
        self.login(u.expert1[0], u.expert1[1])
        data = {'txt': '试', 'txt_type': '', 'is_variant': False, 'task_type': 'cluster_review'}
        r = self.fetch('/api/char/txt/%s' % char1['name'], body={'data': data})
        self.assert_code(200, r)

    def test_update_chars_txt(self):
        """ 测试批量修改"""
        chars = list(self._app.db.char.find({}).limit(2))

        # 测试批量修改
        names = [c['name'] for c in chars]
        txts = [t for t in '测试数据等级' if t not in [c['txt'] for c in chars]]
        self.login(u.expert1[0], u.expert1[1])
        data = {'names': names, 'txt': txts[0], 'task_type': 'cluster_review'}
        r = self.fetch('/api/chars/txt', body={'data': data})
        self.assert_code(200, r)
