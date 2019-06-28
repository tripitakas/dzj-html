#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.users as u
from tests.testcase import APITestCase


class TestText(APITestCase):
    def setUp(self):
        super(TestText, self).setUp()
        self.assert_code(200, self.register_and_login(dict(
            email=u.expert1[0], password=u.expert1[1], name=u.expert1[2])))

    def test_text_simple(self):
        for task_type in [
            # 'text_proof_1', 'text_proof_2', 'text_proof_3',
            'text_review',
        ]:
            r = self.fetch('/task/%s/GL_924_2_35?_raw=1' % task_type)
            self.assert_code(200, r)
            r = self.parse_response(r)
            self.assertIn('cmp_data', r)
            self.assertEqual(r.get('readonly'), True)
