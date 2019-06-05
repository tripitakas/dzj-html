#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase
from controller import errors as e
import re


class TestCharOrder(APITestCase):

    def test_simple(self):
        r = self.fetch('/task/do/char_order_proof/GL_924_2_35?_raw=1&view=1')
        self.assert_code(200, r)
        r = self.parse_response(r)
        self.assertIn('layout', r)
        r = self.parse_response(self.fetch('/task/do/char_order_proof/GL_924_2_35?_raw=1&view=1&layout=2'))
        self.assertEqual(r.get('zero_char_id'), [])

    def test_gen_char_id(self):
        self.assert_code(e.not_allowed_empty, self.fetch('/api/data/gen_char_id', body={}))
        self.assert_code(e.not_allowed_empty, self.fetch('/api/data/gen_char_id',
                                                         body={'data': dict(blocks=[], columns=[], chars=[])}))
        p = self.parse_response(self.fetch('/api/task/page/GL_924_2_35'))  # 单栏
        err_ids = [c['char_id'] for c in p['chars'] if not re.match(r'^b\d+c\d+c\d+', c['char_id'])]
        self.assertTrue(err_ids)
        r = self.fetch('/api/data/gen_char_id', body={'data': p})
        self.assert_code(200, r)
        chars = self.parse_response(r)['chars']
        self.assertFalse([c['char_id'] for c in chars if not re.match(r'^b\d+c\d+c\d+', c['char_id'])])
