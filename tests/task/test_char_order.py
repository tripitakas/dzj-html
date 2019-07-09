#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.users as u
from tests.testcase import APITestCase
import re


class TestCharOrder(APITestCase):
    def setUp(self):
        super(TestCharOrder, self).setUp()
        self.assert_code(200, self.register_and_login(dict(
            email=u.expert1[0], password=u.expert1[1], name=u.expert1[2])))

    def test_simple(self):
        r = self.fetch('/task/char_cut_proof/order/GL_924_2_35?_raw=1')
        self.assert_code(200, r)
        r = self.parse_response(r)
        self.assertIn('chars_col', r)
        r = self.parse_response(self.fetch('/task/char_cut_proof/order/GL_924_2_35?_raw=1&layout=2'))
        self.assertEqual(r.get('zero_char_id'), [])

    def test_gen_char_id(self):
        r = self.parse_response(self.fetch('/api/data/gen_char_id', body={}))
        self.assertIn('KeyError', r.get('message'))
        r = self.fetch('/api/data/gen_char_id', body={'data': dict(blocks=[], columns=[], chars=[])})
        self.assert_code(200, r)

        p = self.parse_response(self.fetch('/api/task/page/GL_924_2_35'))  # 单栏
        self.assertEqual(p.get('status'), 'success')
        err_ids = [c['char_id'] for c in p['chars'] if not re.match(r'^b\d+c\d+c\d+', c['char_id'])]
        self.assertTrue(err_ids)
        r = self.parse_response(self.fetch('/api/data/gen_char_id', body={'data': p}))
        self.assertEqual(p['blocks'], r['blocks'])
        self.assertEqual(p['columns'], r['columns'])
        chars = r['chars']
        err_ids = [c['char_id'] for c in chars if not re.match(r'^b\d+c\d+c\d+', c['char_id'])]
        self.assertEqual(r.get('zero_char_id'), err_ids)
        self.assertFalse(err_ids)
        # self.assertEqual(len(r.get('chars_col', [])), len(p['columns']))
