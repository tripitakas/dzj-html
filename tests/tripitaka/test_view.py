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
            r = self.fetch('/%s/%s?_raw=1&_no_auth=1' % (tripitaka, '1_1'))
            self.assert_code(200, r, msg=tripitaka)
            d = self.parse_response(r)
            self.assertIn('meta', d)

    def test_view_tripitaka_front_cover(self):
        """ 测试藏经阅读-封面图片 """
        r = self.fetch('/QD/1_f1?_raw=1&_no_auth=1')
        self.assert_code(200, r)
        d = self.parse_response(r)
        self.assertIn('meta', d)
