#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase


class TestCharOrder(APITestCase):

    def test_simple(self):
        r = self.fetch('/task/do/char_order_proof/GL_924_2_35?_raw=1&view=1')
        self.assert_code(200, r)
        r = self.parse_response(r)
        self.assertIn('layout', r)
        r = self.parse_response(self.fetch('/task/do/char_order_proof/GL_924_2_35?_raw=1&view=1&layout=2'))
        self.assertEqual(r.get('zero_char_id'), [])
