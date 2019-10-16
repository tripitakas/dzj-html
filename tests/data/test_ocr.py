#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.users as u
from tests.testcase import APITestCase
from controller import errors


class TestOCR(APITestCase):
    def setUp(self):
        super(TestOCR, self).setUp()

        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.data1]], '数据管理员,OCR校对员'
        )

    def test_submit_ocr(self):
        self._app.db.page.delete_one(dict(name='JS_100_527_1'))
        r = self.fetch('/api/data/submit_ocr/JS_100_527_1.gif', body={})
        self.assert_code(200, r)
        r = self.parse_response(r)
        self.assertIn('name', r)
        self.assert_code(errors.ocr_page_existed, self.fetch('/api/data/submit_ocr/JS_100_527_1.gif', body={}))

    def _test_import_images(self):
        """请求批量导入藏经图"""
        self.login(u.data1[0], u.data1[1])
        data = dict(user_code='upload', tripitaka_code='LQ', folder='5-冠導七十五法名目')
        r = self.fetch('/api/data/import_images', body={'data': data})
        self.assert_code(200, r)
        r = self.parse_response(r)
        self.assertIn('names', r)
