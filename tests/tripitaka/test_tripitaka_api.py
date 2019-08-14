#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path
import controller.errors as e
from tests.testcase import APITestCase


class TestTaskFlow(APITestCase):

    def setUp(self):
        super(TestTaskFlow, self).setUp()
        self.add_first_user_as_admin_then_login()

    def tearDown(self):
        super(TestTaskFlow, self).tearDown()

    def test_api_tripitaka_upload(self):
        # 测试上传藏csv文件
        META_DIR = path.join(self._app.BASE_DIR, 'meta', 'meta')
        tripitaka_file = path.join(META_DIR, 'Tripitaka.csv')
        if path.exists(tripitaka_file):
            r = self.fetch('/api/data/upload/tripitaka', files={'csv': tripitaka_file}, body={})
            self.assert_code(200, r)

    def test_api_tripitaka_add_or_update(self):
        tripitaka = self._app.db.tripitaka.find_one()
        # 测试修改一条藏信息
        tripitaka['remark'] = '测试数据'
        r = self.fetch('/api/data/tripitaka', body={'data': tripitaka})
        self.assert_code(200, r)

        # 测试新增一条藏信息
        self._app.db.tripitaka.delete_one({'tripitaka_code': 'YY'})
        tripitaka['tripitaka_code'] = 'YY'
        r = self.fetch('/api/data/tripitaka', body={'data': tripitaka})
        self.assert_code(200, r)

        # 测试藏代码有误
        tripitaka['tripitaka_code'] = '1111'
        r = self.fetch('/api/data/tripitaka', body={'data': tripitaka})
        self.assert_code(e.invalid_tripitaka_code, r)

    def test_api_tripitaka_delete(self):
        tripitakas = list(self._app.db.tripitaka.find().limit(5))
        # 测试删除一条记录
        _id = tripitakas[0].get('_id')
        r = self.fetch('/api/data/tripitaka/delete', body={'data': {'_id': _id}})
        self.assert_code(200, r)

        # 测试删除多条记录
        _ids = [r.get('_id') for r in tripitakas]
        r = self.fetch('/api/data/tripitaka/delete', body={'data': {'_ids': _ids}})
        self.assert_code(200, r)
