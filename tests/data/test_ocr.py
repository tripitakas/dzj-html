#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase
from os import path

sample_path = path.join(path.dirname(path.dirname(__file__)), 'sample')


class TestRecognition(APITestCase):

    def _test_ocr_simple(self):
        img_file = path.join(sample_path, 'JS', 'JS_1_1036.gif')
        r = self.fetch('/api/data/ocr', files={'img': img_file}, body={})
        self.assert_code(200, r)
