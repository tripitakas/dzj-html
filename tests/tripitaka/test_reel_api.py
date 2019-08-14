#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path
from glob2 import glob
import controller.errors as e
from tests.testcase import APITestCase
from controller.tripitaka.volume import Volume


class TestTaskFlow(APITestCase):

    def setUp(self):
        super(TestTaskFlow, self).setUp()
        self.add_first_user_as_admin_then_login()

    def tearDown(self):
        super(TestTaskFlow, self).tearDown()

    def test_api_reel_upload(self):
        # 测试上传卷csv文件
        META_DIR = path.join(self._app.BASE_DIR, 'meta', 'meta')
        files = glob(path.join(META_DIR, 'Reel-*.csv'))
        if files:
            file = files[0]
            for f in files:
                if path.getsize(file) > path.getsize(f):
                    file = f
            file = path.join(META_DIR, 'Reel-QL.csv')
            r = self.fetch('/api/data/reel/upload', files={'csv': file}, body={})
            self.assert_code(200, r)

    def test_api_reel_add_or_update(self):
        reel = self._app.db.reel.find_one()
        # 测试修改一条信息
        reel['remark'] = '测试数据'
        r = self.fetch('/api/data/reel', body={'data': reel})
        self.assert_code(200, r)

        # 测试新增一条信息
        self._app.db.reel.delete_one({'reel_code': 'YY0001_1'})
        reel['reel_code'] = 'YY0001_1'
        r = self.fetch('/api/data/reel', body={'data': reel})
        self.assert_code(200, r)

        # 测试藏代码有误
        reel['reel_code'] = '1111'
        r = self.fetch('/api/data/reel', body={'data': reel})
        self.assert_code(e.invalid_reel_code, r)

    def test_api_reel_delete(self):
        reels = list(self._app.db.reel.find().limit(5))
        # 测试删除一条记录
        _id = reels[0].get('_id')
        r = self.fetch('/api/data/reel/delete', body={'data': {'_id': _id}})
        self.assert_code(200, r)

        # 测试删除多条记录
        _ids = [r.get('_id') for r in reels]
        r = self.fetch('/api/data/reel/delete', body={'data': {'_ids': _ids}})
        self.assert_code(200, r)
