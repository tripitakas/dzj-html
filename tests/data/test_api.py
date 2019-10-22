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

    def test_api_publish_ocr(self):
        docs_ready = ['QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733', 'YB_22_346', 'YB_22_389']
        r = self.fetch('/api/data/publish_ocr', body={'data': dict(force='0', doc_ids=docs_ready)})
        self.assert_code(200, r)

    def test_api_upload_cloud(self):
        docs_ready = ['QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733', 'YB_22_346', 'YB_22_389']
        r = self.fetch('/api/data/upload_cloud', body={'data': dict(force='0', doc_ids=docs_ready)})
        self.assert_code(200, r)
