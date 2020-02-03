#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path
from glob2 import glob
from tests.testcase import APITestCase
import controller.errors as e


class TestTripitakaApi(APITestCase):

    def setUp(self):
        super(TestTripitakaApi, self).setUp()
        self.add_first_user_as_admin_then_login()

    def tearDown(self):
        super(TestTripitakaApi, self).tearDown()

    def test_tripitaka__upload(self):
        # 测试上传csv文件
        META_DIR = path.join(self._app.BASE_DIR, 'meta', 'meta')
        tripitaka_file = path.join(META_DIR, 'Tripitaka.csv')
        if path.exists(tripitaka_file):
            r = self.fetch('/api/data/tripitaka/upload', files={'csv': tripitaka_file}, body={})
            self.assert_code(200, r)

    def test_tripitaka_add_or_update(self):
        tripitaka = self._app.db.tripitaka.find_one()
        # 测试修改一条信息
        tripitaka['tripitaka_code'] = 'CS'
        r = self.fetch('/api/data/tripitaka', body={'data': tripitaka})
        self.assert_code(200, r)

        # 测试新增一条信息
        self._app.db.tripitaka.delete_one({'tripitaka_code': 'YY'})
        tripitaka['tripitaka_code'] = 'YY'
        r = self.fetch('/api/data/tripitaka', body={'data': tripitaka})
        self.assert_code(200, r)

        # 测试代码有误
        tripitaka['tripitaka_code'] = '1111'
        r = self.fetch('/api/data/tripitaka', body={'data': tripitaka})
        self.assert_code(e.invalid_tripitaka_code, r)

    def test_tripitaka_delete(self):
        tripitakas = list(self._app.db.tripitaka.find().limit(5))
        # 测试删除一条记录
        _id = tripitakas[0].get('_id')
        r = self.fetch('/api/data/tripitaka/delete', body={'data': {'_id': _id}})
        self.assert_code(200, r)

        # 测试删除多条记录
        _ids = [r.get('_id') for r in tripitakas]
        r = self.fetch('/api/data/tripitaka/delete', body={'data': {'_ids': _ids}})
        self.assert_code(200, r)

    def test_tripitaka_view(self):
        """ 测试藏经阅读 """
        tripitakas = []
        for _, code in glob(path.join(self._app.BASE_DIR, 'meta', 'meta', 'Volume-*.csv'), True):
            tripitakas.append(code[0])

        for tripitaka in tripitakas:
            r = self.fetch('/page/%s?_raw=1&_no_auth=1' % tripitaka)
            self.assert_code([200, e.img_unavailable, e.no_object], r, msg=tripitaka)
            if self.get_code(r) == 200:
                d = self.parse_response(r)
                self.assertIn('tripitaka', d)
