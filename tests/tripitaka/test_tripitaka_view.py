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

    def test_view_tripitaka(self):
        """ 测试藏经阅读 """
        for _, code in glob(path.join(self._app.BASE_DIR, 'meta', 'meta', 'Volume-*.csv'), True):
            r = self.fetch('/t/%s/%s?_raw=1&_no_auth=1' % (code[0], '1'))
            self.assert_code([200, e.tripitaka_img_not_existed, e.tripitaka_not_existed], r, msg=code[0])
            if self.get_code(r) == 200:
                d = self.parse_response(r)
                self.assertIn('meta', d)
