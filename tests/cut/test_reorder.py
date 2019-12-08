#!/usr/bin/env python
# -*- coding: utf-8 -*-
from os import path
import json
from tests.testcase import APITestCase
from controller.cut.reorder import char_reorder
from controller.cut.cuttool import CutTool


class TestCutReorder(APITestCase):
    def load_sample(self, name):
        return json.load(open(path.join(self._app.BASE_DIR, 'meta/sample/GL/%s.json' % name)))

    def get_column_txt(self, chars, column_id):
        return ''.join([c['txt'] for c in chars if column_id in c['char_id']])

    def test_cut_reorder_simple(self):
        page = self.load_sample('GL_1056_5_6')
        columns = char_reorder(page['chars'], page['blocks'])
        if columns is not None:
            for c in columns:
                self.assertGreater(c['block_no'], 0)
                self.assertGreater(c['line_no'], 0)
            for c in page['chars']:
                self.assertGreater(c['block_no'], 0)
                self.assertGreater(c['line_no'], 0)
                self.assertGreater(c['char_no'], 0)

    def test_cut_reorder_add_remove_char(self):
        page = self.load_sample('GL_1056_5_6')
        columns = char_reorder(page['chars'], page['blocks'])
        if columns:
            self.assertEqual(self.get_column_txt(page['chars'], 'b1c1c'), '衆經目録卷苐五苐六張設N来')

            chars1 = page['chars'] + [dict(x=5608, y=1080, w=106, h=136, txt='加')]  # 在右上角加个字框
            columns1 = char_reorder(chars1, page['blocks'])
            self.assertEqual(chars1[0]['txt'], '加')  # 新字框变为第一个字框
            self.assertEqual(len(columns1), len(columns))
            self.assertEqual('加衆經目録卷苐五苐六張設N来', self.get_column_txt(chars1, 'b1c1c'))

            chars2 = page['chars'][2:]  # 去掉两个字框：衆經
            columns1 = char_reorder(chars2, page['blocks'])
            self.assertEqual(chars2[0]['txt'], '目')
            self.assertEqual(len(columns1), len(columns))
            self.assertEqual('目録卷苐五苐六張設N来',
                             ''.join([c['txt'] for c in chars2 if 'b1c1c' in c['char_id']]))

    def test_cut_reorder_merge_column(self):
        def find_by_xy(x, y):
            ret = [c for c in page['chars'] if int(c['x']) == x and int(c['y']) == y]
            return ret and ret[0]

        page = self.load_sample('GL_1056_5_6')
        chars = page['chars']
        columns = char_reorder(chars, page['blocks'])
        if columns:
            fen, shi = find_by_xy(5129, 758), find_by_xy(5396, 781)  # 右上第二、三列的首字框
            self.assertEqual(fen['char_id'], 'b1c3c1')
            self.assertEqual(shi['char_id'], 'b1c2c1')
            self.assertEqual('分別六情經一卷', self.get_column_txt(chars, 'b1c3c'))
            self.assertEqual('十思惟經一卷', self.get_column_txt(chars, 'b1c2c'))

            chars.remove(shi)
            fen['w'] = 418  # 让“分”跨两列
            columns1 = char_reorder(chars, page['blocks'])

            self.assertEqual(len(columns1), len(columns) - 1)
            self.assertEqual(columns1[0], columns[0])
            self.assertEqual([(c['x'], c['y']) for c in columns1[1:]],
                             [(c['x'], c['y']) for c in columns[2:]])

            self.assertEqual(fen['char_id'], 'b1c2c1')  # “分”从第三列变为第二列
            # self.assertEqual('分思惟經一卷別六情經一卷', self.get_column_txt(chars, 'b1c2c'))  错！
            self.assertEqual('後出阿弥陁佛偈一卷貞觀九年入正目訖',
                             self.get_column_txt(chars, 'b1c12c'))
            self.assertEqual('迦旃延偈經一卷沒一名盡迦偈旃百延二十說章法貞觀九年入正目訖',
                             self.get_column_txt(chars, 'b1c13c'))  # 错
            self.assertEqual('菩薩戒經一卷北鿌沮渠蒙遜世沙門曇無䜟於姑𮍏譯',
                             self.get_column_txt(chars, 'b1c17c'))
            self.assertEqual('佛悔過經一卷𣈆世沙門笁法護譯',
                             self.get_column_txt(chars, 'b1c18c'))

            # OCR排序模块是按从左到右、从上到下的顺序排序的，改用v2算法在列内重新排序
            chars2 = json.loads(json.dumps(chars))
            columns2 = json.loads(json.dumps(columns1))
            CutTool.sort_chars(chars2, columns2, page['blocks'], 2)

            self.assertEqual(columns1, columns2)
            self.assertEqual([c for c in chars if 'b1c1c' in c['char_id']],
                             [c for c in chars2 if 'b1c1c' in c['char_id']])
            for line_no in range(3, 13):
                self.assertEqual([c for c in chars if 'b1c%dc' % line_no in c['char_id']],
                                 [c for c in chars2 if 'b1c%dc' % line_no in c['char_id']])

            # self.assertEqual('分思惟經一卷別六情經一卷', self.get_column_txt(chars2, 'b1c2c'))  错！
            self.assertEqual('後出阿弥陁佛偈一卷貞觀九年入正目訖',
                             self.get_column_txt(chars2, 'b1c12c'))
            self.assertEqual('菩薩戒經一卷北鿌沮渠蒙遜世沙門曇無䜟於姑𮍏譯',
                             self.get_column_txt(chars2, 'b1c17c'))
            self.assertEqual('佛悔過經一卷𣈆世沙門笁法護譯',
                             self.get_column_txt(chars2, 'b1c18c'))
            self.assertEqual('迦旃延偈經一卷一名迦旃延說法沒盡偈百二十章貞觀九年入正目訖',
                             self.get_column_txt(chars2, 'b1c13c'))  # 错
