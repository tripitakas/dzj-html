#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from os import path
from glob2 import glob
from tests.testcase import APITestCase
import controller.errors as e


class TestPageApi(APITestCase):

    def setUp(self):
        super(TestPageApi, self).setUp()
        self.add_first_user_as_admin_then_login()

    def tearDown(self):
        super(TestPageApi, self).tearDown()

    def test_api_page__upload(self):
        # 测试上传页面json文件
        filename = path.join(self._app.BASE_DIR, 'meta', 'meta', 'pages.json')
        if not path.exists(filename):
            return

        # 清空上次的数据
        with open(filename, 'r') as fn:
            page_names = json.load(fn)
            self._app.db.page.delete_many({'name': {'$in': page_names}})

        r = self.fetch('/api/data/page/upload', files={'json': filename}, body={})
        self.assert_code(200, r)
