#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase


class TestSpecialText(APITestCase):

    def test_utf8mb4(self):
        r = self.fetch('/api/get/text/GL_1056_5_6')
        self.assert_code(200, r)
        txt = self.parse_response(r).get('txt', '')
        self.assertIn('卷北鿌沮渠蒙遜', txt)
        self.assertIn('\U0002e34f', txt)
