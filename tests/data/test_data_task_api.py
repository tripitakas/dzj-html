#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path
from glob2 import glob
from tests.testcase import APITestCase
import controller.errors as e


class TestApi(APITestCase):

    def setUp(self):
        super(TestApi, self).setUp()
        self.add_first_user_as_admin_then_login()

    def tearDown(self):
        super(TestApi, self).tearDown()

    def test_api_publish_data_task(self):
        for data_task in ['ocr', 'upload_cloud']:
            docs_ready = ['QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733', 'YB_22_346', 'YB_22_389']
            r = self.fetch('/api/data/publish/' + data_task, body={'data': dict(force='0', doc_ids=docs_ready)})
            self.assert_code(200, r)

        for data_task in ['import_image']:
            r = self.fetch('/api/data/publish/' + data_task, body={'data': dict(dir='/srv/home/test', redo='0')})
            self.assert_code(200, r)

    def test_api_pick_data_task(self):
        for data_task in ['ocr', 'upload_cloud']:
            r = self.fetch('/api/data/pick/' + data_task, body={'data': {'size': 2}})
            self.assert_code(200, r)

        for data_task in ['import_image']:
            r = self.fetch('/api/data/pick/' + data_task, body={'data': {}})
            self.assert_code(200, r)

    def test_api_submit_data_task(self):
        data_task = 'ocr'
        pages = list(self._app.db.page.find({'name': {'$in': ['QL_25_16', 'QL_25_313']}}))
        r = self.fetch('/api/data/submit/' + data_task, body={'data': {'result': pages}})
        self.assert_code(200, r)

        data_task = 'upload_cloud'
        pages = [{'name': 'QL_25_16', 'status': 'success'},
                 {'name': 'QL_25_313', 'status': 'failed', 'message': '图片格式有误'}]
        r = self.fetch('/api/data/submit/' + data_task, body={'data': {'result': pages}})
        self.assert_code(200, r)

        data_task = 'import_image'
        one_import = self._app.db['import'].find_one()
        data = dict(_id=str(one_import['_id']), status='failed', message='图片路径有误')
        r = self.fetch('/api/data/submit/' + data_task, body={'data': data})
        self.assert_code(200, r)
