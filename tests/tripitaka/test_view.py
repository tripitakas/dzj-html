#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase


class TestTaskFlow(APITestCase):

    def setUp(self):
        super(TestTaskFlow, self).setUp()
        self.add_first_user_as_admin_then_login()

    def tearDown(self):
        super(TestTaskFlow, self).tearDown()

    def test_view_tripitaka(self):
        """ 测试藏经阅读 """
        tripitakas = ['GL', 'LC', 'JX', 'FS', 'HW', 'QD', 'PL', 'QS', 'SX', 'YB', 'ZH', 'QL']
        for tripitaka in tripitakas:
            r = self.fetch('/tripitaka/%s?_raw=1&_no_auth=1' % tripitaka)
            self.assert_code(200, r, msg=tripitaka)
            d = self.parse_response(r)
            pass


