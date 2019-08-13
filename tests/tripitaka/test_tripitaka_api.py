#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path
from glob2 import glob
from tests.testcase import APITestCase


class TestTaskFlow(APITestCase):

    def setUp(self):
        super(TestTaskFlow, self).setUp()
        self.add_first_user_as_admin_then_login()

    def tearDown(self):
        super(TestTaskFlow, self).tearDown()

    def test_tripitaka_api_upload(self):
        META_DIR = path.join(self._app.BASE_DIR, 'meta', 'meta')

        # 测试上传藏csv文件
        tripitaka_file = path.join(META_DIR, 'Tripitaka.csv')
        if path.exists(tripitaka_file):
            r = self.fetch('/api/data/upload/tripitaka', files={'csv': tripitaka_file}, body={})
            self.assert_code(200, r)

        # 测试上传册csv文件
        files = glob(path.join(META_DIR, 'Volume-*.csv'))
        if files:
            file = files[0]
            for f in files:
                if path.getsize(file) > path.getsize(f):
                    file = f
            r = self.fetch('/api/data/upload/volume', files={'csv': file}, body={})
            self.assert_code(200, r)

        # 测试上传经csv文件
        files = glob(path.join(META_DIR, 'Sutra-*.csv'))
        if files:
            file = files[0]
            for f in files:
                if path.getsize(file) > path.getsize(f):
                    file = f
            r = self.fetch('/api/data/upload/sutra', files={'csv': file}, body={})
            self.assert_code(200, r)

        # 测试上传卷csv文件
        files = glob(path.join(META_DIR, 'Reel-*.csv'))
        if files:
            file = files[0]
            for f in files:
                if path.getsize(file) > path.getsize(f):
                    file = f
            r = self.fetch('/api/data/upload/reel', files={'csv': file}, body={})
            self.assert_code(200, r)
