#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase
from controller.diff import Diff


class TestDiff(APITestCase):
    base = '一二三四五六七八九十百千万'
    cmp1 = '一二改四五增六七减十百千万'
    cmp2 = '一二三改五六增七八减百千万'
    cmp3 = '二三四五六七八九十百千万一'
    diff1 = [
        {'line_no': 1, 'seg_no': 1, 'is_same': True, 'base': '一二', 'cmp1': '一二'},
        {'line_no': 1, 'seg_no': 2, 'is_same': False, 'base': '三', 'cmp1': '改'},
        {'line_no': 1, 'seg_no': 3, 'is_same': True, 'base': '四五', 'cmp1': '四五'},
        {'line_no': 1, 'seg_no': 4, 'is_same': False, 'base': '', 'cmp1': '增'},
        {'line_no': 1, 'seg_no': 5, 'is_same': True, 'base': '六七', 'cmp1': '六七'},
        {'line_no': 1, 'seg_no': 6, 'is_same': False, 'base': '八九', 'cmp1': '减'},
        {'line_no': 1, 'seg_no': 7, 'is_same': True, 'base': '十百千万', 'cmp1': '十百千万'}
    ]
    diff2 = [
        {'line_no': 1, 'seg_no': 1, 'is_same': True, 'base': '一二三', 'cmp2': '一二三'},
        {'line_no': 1, 'seg_no': 2, 'is_same': False, 'base': '四', 'cmp2': '改'},
        {'line_no': 1, 'seg_no': 3, 'is_same': True, 'base': '五六', 'cmp2': '五六'},
        {'line_no': 1, 'seg_no': 4, 'is_same': False, 'base': '', 'cmp2': '增'},
        {'line_no': 1, 'seg_no': 5, 'is_same': True, 'base': '七八', 'cmp2': '七八'},
        {'line_no': 1, 'seg_no': 6, 'is_same': False, 'base': '九十', 'cmp2': '减'},
        {'line_no': 1, 'seg_no': 7, 'is_same': True, 'base': '百千万', 'cmp2': '百千万'}
    ]
    diff3 = [
        {'line_no': 1, 'seg_no': 1, 'is_same': False, 'base': '一', 'cmp3': ''},
        {'line_no': 1, 'seg_no': 2, 'is_same': True, 'base': '二三四五六七八九十百千万', 'cmp3': '二三四五六七八九十百千万'},
        {'line_no': 1, 'seg_no': 3, 'is_same': False, 'base': '', 'cmp3': '一'}
    ]
    merge12 = [
        {'line_no': 1, 'seg_no': 1, 'is_same': True, 'base': '一二', 'cmp1': '一二', 'cmp2': '一二'},
        {'line_no': 1, 'seg_no': 2, 'is_same': False, 'base': '三四', 'cmp1': '改四', 'cmp2': '三改'},
        {'line_no': 1, 'seg_no': 3, 'is_same': True, 'base': '五', 'cmp1': '五', 'cmp2': '五'},
        {'line_no': 1, 'seg_no': 4, 'is_same': False, 'base': '', 'cmp1': '增', 'cmp2': ''},
        {'line_no': 1, 'seg_no': 5, 'is_same': True, 'base': '六', 'cmp1': '六', 'cmp2': '六'},
        {'line_no': 1, 'seg_no': 6, 'is_same': False, 'base': '', 'cmp1': '', 'cmp2': '增'},
        {'line_no': 1, 'seg_no': 7, 'is_same': True, 'base': '七', 'cmp1': '七', 'cmp2': '七'},
        {'line_no': 1, 'seg_no': 8, 'is_same': False, 'base': '八九十', 'cmp1': '减十', 'cmp2': '八减'},
        {'line_no': 1, 'seg_no': 9, 'is_same': True, 'base': '百千万', 'cmp1': '百千万', 'cmp2': '百千万'}
    ]
    merge123 = [
        {'line_no': 1, 'seg_no': 1, 'is_same': False, 'base': '一', 'cmp1': '一', 'cmp2': '一', 'cmp3': ''},
        {'line_no': 1, 'seg_no': 2, 'is_same': True, 'base': '二', 'cmp1': '二', 'cmp2': '二', 'cmp3': '二'},
        {'line_no': 1, 'seg_no': 3, 'is_same': False, 'base': '三四', 'cmp1': '改四', 'cmp2': '三改', 'cmp3': '三四'},
        {'line_no': 1, 'seg_no': 4, 'is_same': True, 'base': '五', 'cmp1': '五', 'cmp2': '五', 'cmp3': '五'},
        {'line_no': 1, 'seg_no': 5, 'is_same': False, 'base': '', 'cmp1': '增', 'cmp2': '', 'cmp3': ''},
        {'line_no': 1, 'seg_no': 6, 'is_same': True, 'base': '六', 'cmp1': '六', 'cmp2': '六', 'cmp3': '六'},
        {'line_no': 1, 'seg_no': 7, 'is_same': False, 'base': '', 'cmp1': '', 'cmp2': '增', 'cmp3': ''},
        {'line_no': 1, 'seg_no': 8, 'is_same': True, 'base': '七', 'cmp1': '七', 'cmp2': '七', 'cmp3': '七'},
        {'line_no': 1, 'seg_no': 9, 'is_same': False, 'base': '八九十', 'cmp1': '减十', 'cmp2': '八减', 'cmp3': '八九十'},
        {'line_no': 1, 'seg_no': 10, 'is_same': True, 'base': '百千万', 'cmp1': '百千万', 'cmp2': '百千万', 'cmp3': '百千万'}
    ]

    base_lines = """一二三四五六七八九十
        二三四五六七八九十一
        三四五六七八九十一二
        四五六七八九十一二三"""
    cmp_lines1 = """一二三四五六七八九
        十二三四五六七八九十一
        三四五六七八九十一二
        四五六七八九十一二三"""
    cmp_lines2 = """二三四五六七八九十一
        三四五六七八九十一二"""
    cmp_lines3 = """一二三四五六七八九十
        二三四五六七八九十一
        三四五六七八九十一二
        四五六七八九十一二三"""

    diffs1 = [
        {'line_no': 1, 'seg_no': 1, 'is_same': True, 'base': '一二三四五六七八九', 'cmp1': '一二三四五六七八九'},
        {'line_no': 1, 'seg_no': 2, 'is_same': False, 'base': '', 'cmp1': '\n'},
        {'line_no': 1, 'seg_no': 3, 'is_same': True, 'base': '十', 'cmp1': '十'},
        {'line_no': 2, 'seg_no': 1, 'is_same': True, 'base': '二三四五六七八九十一', 'cmp1': '二三四五六七八九十一'},
        {'line_no': 3, 'seg_no': 1, 'is_same': True, 'base': '三四五六七八九十一二', 'cmp1': '三四五六七八九十一二'},
        {'line_no': 4, 'seg_no': 1, 'is_same': True, 'base': '四五六七八九十一二三', 'cmp1': '四五六七八九十一二三'}
    ]
    diffs2 = [
        {'line_no': 1, 'seg_no': 1, 'is_same': False, 'base': '一二三四五六七八九十', 'cmp1': ''},
        {'line_no': 2, 'seg_no': 1, 'is_same': True, 'base': '二三四五六七八九十一', 'cmp1': '二三四五六七八九十一'},
        {'line_no': 3, 'seg_no': 1, 'is_same': True, 'base': '三四五六七八九十一二', 'cmp1': '三四五六七八九十一二'},
        {'line_no': 4, 'seg_no': 1, 'is_same': False, 'base': '四五六七八九十一二三', 'cmp1': ''}
    ]

    def test_merge_diff_pos(self):
        diff_pos1 = [(3, 5), (8, 10), (11, 14)]
        diff_pos2 = [(0, 1), (5, 8)]
        r = Diff._merge_diff_pos(diff_pos1, diff_pos2)
        self.assertEqual(r, [(0, 1), (3, 10), (11, 14)])

    def test_merge_by_combine(self):
        m12, e12 = Diff._merge_by_combine(self.diff1, self.diff2)
        self.assertEqual(m12, self.merge12)
        m123, e123 = Diff._merge_by_combine(m12, self.diff3)
        self.assertEqual(m123, self.merge123)

    def test_diff_one_line(self):
        ret1, err1 = Diff.diff(self.base, self.cmp1, label=dict(base='base', cmp1='cmp1'))
        self.assertEqual(ret1, self.diff1)
        ret2, err2 = Diff.diff(self.base, self.cmp2, label=dict(base='base', cmp1='cmp2'))
        self.assertEqual(ret2, self.diff2)
        ret3, err3 = Diff.diff(self.base, self.cmp3, label=dict(base='base', cmp1='cmp3'))
        self.assertEqual(ret3, self.diff3)
        ret12, err12 = Diff.diff(self.base, self.cmp1, self.cmp2)
        self.assertEqual(ret12, self.merge12)
        ret123, err123 = Diff.diff(self.base, self.cmp1, self.cmp2, self.cmp3)
        self.assertEqual(ret123, self.merge123)

    def test_diff_lines(self):
        #ret1, err1 = Diff.diff(self.base_lines, self.cmp_lines1)
        #self.assertEqual(ret1, self.diffs1)
        ret2, err2 = Diff.diff(self.base_lines, self.cmp_lines2)
        self.assertEqual(ret2, self.diffs2)
