#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.users as u
from controller import errors as e
from tests.testcase import APITestCase
from tornado.escape import json_encode
from controller.char.base import CharHandler as Ch


class TestChar(APITestCase):
    task_types = list(Ch.get_char_tasks().keys())
    char_names = ['QL_25_16_1', 'QL_25_313_1', 'QL_25_416_11', 'QL_25_733_11', 'YB_22_346_11', 'YB_22_389_11']

    def setUp(self):
        super(TestChar, self).setUp()
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3, u.expert3]],
            '切分专家,文字专家,聚类校对员,聚类审定员'
        )
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.proof1, u.proof2, u.proof3]],
            '普通用户,单元测试用户,切分校对员,聚类校对员,生僻校对员'
        )
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.review1, u.review2, u.review3]],
            '普通用户,单元测试用户,切分审定员,聚类审定员,生僻审定员'
        )

    def tearDown(self):
        super(TestChar, self).tearDown()

    def test_char_txt(self):
        """ 测试单字修改"""
        char = self._app.db.char.find_one({})
        self._app.db.char.update_one({'_id': char['_id']}, {'$unset': {'txt_level': '', 'txt_logs': ''}})

        # 以校对员一身份登录
        self.login(u.proof1[0], u.proof1[1])

        # 测试直接修改数据-积分不够
        txts = [t for t in '测试单字修改' if t != char['txt']]
        data = {'txt': txts[0], 'txt_type': ''}
        r = self.fetch('/api/char/txt/%s' % char['name'], body={'data': data})
        self.assert_code(e.data_point_unqualified, r)

        # 测试以任务方式修改数据
        data = {'txt': txts[0], 'txt_type': '', 'task_type': 'cluster_proof'}
        r = self.fetch('/api/char/txt/%s' % char['name'], body={'data': data})
        self.assert_code(200, r)
        # 检查数据等级已经修改
        char1 = self._app.db.char.find_one({'_id': char['_id']})
        self.assertIsNotNone(char1.get('txt_logs'))
        self.assertIsNotNone(char1.get('txt_level'))

        # 测试校对员二可以以任务方式修改数据
        self.login(u.proof2[0], u.proof2[1])
        data = {'txt': txts[1], 'txt_type': '', 'task_type': 'cluster_proof'}
        r = self.fetch('/api/char/txt/%s' % char1['name'], body={'data': data})
        self.assert_code(200, r)
        char2 = self._app.db.char.find_one({'_id': char['_id']})
        self.assertEqual(2, len(char2.get('txt_logs')))

        # 测试专家一可以直接修改数据
        self.login(u.expert1[0], u.expert1[1])
        data = {'txt': txts[2], 'txt_type': ''}
        r = self.fetch('/api/char/txt/%s' % char1['name'], body={'data': data})
        self.assert_code(200, r)
        char3 = self._app.db.char.find_one({'_id': char['_id']})
        self.assertEqual(3, len(char3.get('txt_logs')))

    def test_chars_txt(self):
        """ 测试批量修改"""
        chars = list(self._app.db.char.find({}).limit(2))
        cond = {'_id': {'$in': [c['_id'] for c in chars]}}
        self._app.db.char.update_many(cond, {'$unset': {'txt_level': '', 'txt_logs': ''}})

        # 测试以任务的方式批量修改
        self.login(u.proof1[0], u.proof1[1])
        names = [c['name'] for c in chars]
        txts = [t for t in '测试数据等级' if t not in [c['txt'] for c in chars]]
        data = {'names': names, 'txt': txts[0], 'task_type': 'cluster_proof'}
        r = self.fetch('/api/chars/txt', body={'data': data})
        self.assert_code(200, r)
        # 检查数据等级已经修改
        char1 = self._app.db.char.find_one({'_id': chars[0]['_id']})
        self.assertIsNotNone(char1.get('txt_logs'))
        self.assertIsNotNone(char1.get('txt_level'))
