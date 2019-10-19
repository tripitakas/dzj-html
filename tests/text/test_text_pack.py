#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase
from controller.text.pack import TextPack as TextPack


class TestTextPack(APITestCase):

    def _test_gen_segments_simple(self):
        """测试文字校对生成标记文本--基本测试"""
        s = TextPack.check_segments('卷北鿌沮渠蒙遜N', [])
        self.assertTrue(len(s) == 1 and isinstance(s[0], dict))
        self.assertEqual(s[0].get('base'), [
            '%E5%8D%B7', '%E5%8C%97', '%E9%BF%8C',
            '%E6%B2%AE', '%E6%B8%A0', '%E8%92%99',
            '%E9%81%9C', 'N'])

        s = TextPack.check_segments('N \U0002e34f', [])  # GL_1056_5_6
        self.assertEqual([c.get('type') for c in s], ['same', 'variant'])
        self.assertEqual(s[0].get('base'), ['N', '+'])
        self.assertEqual(s[1].get('base'), ['%F0%AE%8D%8F'])

        s = TextPack.check_segments('平等無傾囬邪自致𥼶氏云', [])  # GL_1260_4_8
        self.assertEqual([c.get('type') for c in s], ['same', 'variant', 'same'])
        self.assertEqual(s[1].get('base'), ['%F0%A5%BC%B6'])

    def _test_gen_segments_simple_chars(self):
        """测试文字校对生成标记文本--基本字框测试"""
        chars = [
            {'x': 3238, 'y': 2048, 'w': 104, 'h': 100, 'cc': 0.7869, 'char_id': 'b1c11c8'},
            {'x': 3247, 'y': 2204, 'w': 95, 'h': 119, 'cc': 0.8536, 'char_id': 'b1c11c9'},
            {'x': 3253, 'y': 2374, 'w': 83, 'h': 90, 'cc': 0.7215, 'char_id': 'b1c11c10'},
            {'x': 3118, 'y': 915, 'w': 85, 'h': 82, 'cc': 0.8954, 'char_id': 'b1c11c11'}]
        s = TextPack.check_segments('致𥼶氏 云', chars)
        self.assertEqual([c.get('txt') for c in chars], ['致', '𥼶', '氏', '云'])
        self.assertEqual([c.get('base') for c in s], [['%E8%87%B4'], ['%F0%A5%BC%B6'], ['%E6%B0%8F', '+', '%E4%BA%91']])

    def _test_gen_segments_mismatch_lines(self):
        """测试文字校对生成标记文本--图文不匹配"""
        page = self._app.db.page.find_one(dict(name='YB_24_119'))  # 小字与相邻大字误在同一列
        if page:
            self.assertIn('chars', page)
            params = dict(page=page, mismatch_lines=[])
            TextPack.check_segments(page['ocr'], page['chars'], params)
            self.assertEqual(set(params['mismatch_lines']), {'b1c6', 'b1c7'})
