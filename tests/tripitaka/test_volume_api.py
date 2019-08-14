#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path
from glob2 import glob
import controller.errors as e
from tests.testcase import APITestCase


class TestTaskFlow(APITestCase):

    def setUp(self):
        super(TestTaskFlow, self).setUp()
        self.add_first_user_as_admin_then_login()

    def tearDown(self):
        super(TestTaskFlow, self).tearDown()

    def test_api_volume_upload(self):
        # 测试上传csv文件
        META_DIR = path.join(self._app.BASE_DIR, 'meta', 'meta')
        files = glob(path.join(META_DIR, 'Volume-*.csv'))
        if files:
            file = files[0]
            for f in files:
                if path.getsize(file) > path.getsize(f):
                    file = f
            r = self.fetch('/api/data/volume/upload', files={'csv': file}, body={})
            self.assert_code(200, r)

    def test_api_volume_add_or_update(self):
        volume = self._app.db.volume.find_one()
        # 测试修改一条信息
        volume['remark'] = '测试数据'
        r = self.fetch('/api/data/volume', body={'data': volume})
        self.assert_code(200, r)

        # 测试新增一条信息
        self._app.db.volume.delete_one({'volume_code': 'YY_1'})
        volume['volume_code'] = 'YY_1'
        volume.pop('_id', 0)
        r = self.fetch('/api/data/volume', body={'data': volume})
        self.assert_code(200, r)

        # 测试代码有误
        volume['volume_code'] = '1111'
        r = self.fetch('/api/data/volume', body={'data': volume})
        self.assert_code(e.invalid_tripitaka_code, r)

    def test_api_volume_delete(self):
        volumes = list(self._app.db.volume.find().limit(5))
        # 测试删除一条记录
        _id = volumes[0].get('_id')
        r = self.fetch('/api/data/volume/delete', body={'data': {'_id': _id}})
        self.assert_code(200, r)

        # 测试删除多条记录
        _ids = [r.get('_id') for r in volumes]
        r = self.fetch('/api/data/volume/delete', body={'data': {'_ids': _ids}})
        self.assert_code(200, r)
