#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase
from glob2 import glob
from os import path
import controller.errors as e


class TestTripitakaView(APITestCase):

    def setUp(self):
        super(TestTripitakaView, self).setUp()
        self.add_first_user_as_admin_then_login()

    def tearDown(self):
        super(TestTripitakaView, self).tearDown()

    def test_view_tripitaka(self):
        """ 测试藏经阅读 """
        tripitakas = []
        for _, code in glob(path.join(self._app.BASE_DIR, 'meta', 'meta', 'Volume-*.csv'), True):
            tripitakas.append(code[0])

        for tripitaka in tripitakas:
            r = self.fetch('/t/%s?_raw=1&_no_auth=1' % tripitaka)
            self.assert_code([200, e.tptk_img_unavailable], r, msg=tripitaka)
            if self.get_code(r) == 200:
                d = self.parse_response(r)
                self.assertIn('tripitaka', d)
