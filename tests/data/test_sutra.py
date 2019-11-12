#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path
from glob2 import glob
from tests.testcase import APITestCase
import controller.errors as e


class TestSutraApi(APITestCase):

    def setUp(self):
        super(TestSutraApi, self).setUp()
        self.add_first_user_as_admin_then_login()

    def tearDown(self):
        super(TestSutraApi, self).tearDown()

    def test_api_sutra__upload(self):
        # 测试上传经csv文件
        META_DIR = path.join(self._app.BASE_DIR, 'meta', 'meta')
        files = glob(path.join(META_DIR, 'Sutra-*.csv'))
        if files:
            file = files[0]
            for f in files:
                if path.getsize(file) > path.getsize(f):
                    file = f
            r = self.fetch('/api/data/sutra/upload', files={'csv': file}, body={})
            self.assert_code(200, r)

    def test_api_sutra_add_or_update(self):
        sutra = self._app.db.sutra.find_one()
        # 测试修改一条信息
        sutra['remark'] = '测试数据'
        r = self.fetch('/api/data/sutra', body={'data': sutra})
        self.assert_code(200, r)

        # 测试新增一条信息
        self._app.db.sutra.delete_one({'sutra_code': 'YY0001'})
        sutra['sutra_code'] = 'YY0001'
        r = self.fetch('/api/data/sutra', body={'data': sutra})
        self.assert_code(200, r)

        # 测试代码有误
        sutra['sutra_code'] = '1111'
        r = self.fetch('/api/data/sutra', body={'data': sutra})
        self.assert_code(e.invalid_sutra_code, r)

    def test_api_sutra_delete(self):
        sutras = list(self._app.db.sutra.find().limit(5))
        # 测试删除一条记录
        _id = sutras[0].get('_id')
        r = self.fetch('/api/data/sutra/delete', body={'data': {'_id': _id}})
        self.assert_code(200, r)

        # 测试删除多条记录
        _ids = [r.get('_id') for r in sutras]
        r = self.fetch('/api/data/sutra/delete', body={'data': {'_ids': _ids}})
        self.assert_code(200, r)
