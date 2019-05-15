#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase
from controller.task.api_text import CharProofDetailHandler as Proof


class TestTextTaskSegment(APITestCase):

    def test_gen_segments_simple(self):
        s = Proof.gen_segments('卷北鿌沮渠蒙遜N', [])
        self.assertTrue(len(s) == 1 and isinstance(s[0], dict))
        self.assertEqual(s[0].get('ocr'), [
            '%E5%8D%B7', '%E5%8C%97', '%E9%BF%8C',
            '%E6%B2%AE', '%E6%B8%A0', '%E8%92%99',
            '%E9%81%9C', 'N'])

        s = Proof.gen_segments('N \U0002e34f', [])
        self.assertEqual([c.get('type') for c in s], ['same', 'variant'])
        self.assertEqual(s[0].get('ocr'), ['N', '+'])
        self.assertEqual(s[1].get('ocr'), ['%F0%AE%8D%8F'])
