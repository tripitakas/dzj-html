#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase
import controller.errors as e
from glob2 import glob
from os import path


class TestTaskFlow(APITestCase):

    def setUp(self):
        super(TestTaskFlow, self).setUp()
        self.add_first_user_as_admin_then_login()

    def tearDown(self):
        super(TestTaskFlow, self).tearDown()

    def test_tripitaka_api_upload(self):
        meta_dir = path.join(self._app.BASE_DIR, 'meta', 'meta')

        # 测试上传藏经csv文件
        tripitaka_file = path.join(meta_dir, 'Tripitaka.csv')
        r = self.fetch('/api/user/my/avatar', files={'csv': tripitaka_file}, body={})
        self.assert_code(200, r)
