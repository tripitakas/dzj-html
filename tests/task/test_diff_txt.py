#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tests.testcase import APITestCase
from controller.data.diff import Diff


class TestDiff(APITestCase):

    def test_merge_diff_pos(self):
        p1 = [(2, 4), (5, 5), (7, 9)]
        p2 = [(4, 5), (5, 5), (10, 10), (13, 15)]
        r = Diff._merge_diff_pos(p1, p2)
        self.assertEqual(r, [(2, 5), (5, 5), (7, 9), (10, 10), (13, 15)])

        p1 = [(2, 4), (5, 5), (7, 9)]
        p2 = [(4, 6), (10, 10), (13, 15)]
        r = Diff._merge_diff_pos(p1, p2)
        self.assertEqual(r, [(2, 6), (7, 9), (10, 10), (13, 15)])

        p1 = [(0, 1)]
        p2 = [(0, 17)]
        r = Diff._merge_diff_pos(p1, p2)
        self.assertEqual(r, [(0, 17)])

    def _assert_diff(self, diff, base, cmp1, cmp2=None, cmp3=None, label=None):
        lbl = dict(base='base', cmp1='cmp1', cmp2='cmp2', cmp3='cmp3')
        if label:
            lbl.update(label)

        # 检查文本没有遗漏
        base_str = Diff.pre_cmp(''.join([d[lbl['base']] for d in diff]))
        base = Diff.pre_cmp(base)
        self.assertEqual(base_str, base)

        cmp1_str = Diff.pre_cmp(''.join([d.get(lbl['cmp1'], '') for d in diff]))
        cmp1 = Diff.pre_cmp(cmp1)
        self.assertEqual(cmp1_str, cmp1)

        if cmp2:
            cmp2_str = Diff.pre_cmp(''.join([d.get(lbl['cmp2'], '') for d in diff]))
            cmp2 = Diff.pre_cmp(cmp2)
            self.assertEqual(cmp2_str, cmp2)

        if cmp3:
            cmp3_str = Diff.pre_cmp(''.join([d.get(lbl['cmp3'], '') for d in diff]))
            cmp3 = Diff.pre_cmp(cmp3)
            self.assertEqual(cmp3_str, cmp3)

    def test_diff_one_line(self):
        base = """天地玄黄宇  宙洪荒日月盈昃辰宿列张寒  来  暑  往秋收冬藏闰余成岁律吕调阳""".replace(' ', '')
        cmp1 = """天地改黄宇增宙洪  日月    辰宿改张寒增来  暑  往  收冬藏闰余成岁律吕调阳""".replace(' ', '')
        cmp2 = """天地变黄宇加宙洪  日月    辰宿列变寒  来加暑  往秋  冬藏闰余成岁律吕调阳""".replace(' ', '')
        cmp3 = """天地更黄宇附宙洪  日月    辰更列张寒  来  暑附往秋收  藏闰余成岁律吕调阳""".replace(' ', '')
        ret1, err1 = Diff.diff(base, cmp1, label=dict(cmp1='cmp1'))
        ret2, err2 = Diff.diff(base, cmp2, label=dict(cmp1='cmp2'))
        ret3, err3 = Diff.diff(base, cmp3, label=dict(cmp1='cmp3'))

        ret12, err12 = Diff._merge_by_combine(ret1, ret2)
        self.assertEqual(len(ret12), 18)
        base_str = ''.join([d['base'] for d in ret12 if d['base'] != '\n'])
        self.assertEqual(base_str, base)

        r12, e12 = Diff.diff(base, cmp1, cmp2)
        self.assertEqual(len(r12), 18)
        base_str = ''.join([d['base'] for d in r12 if d['base'] != '\n'])
        self.assertEqual(base_str, base)

        ret123, err12 = Diff._merge_by_combine(ret12, ret3)
        self.assertEqual(len(ret123), 20)
        base_str = ''.join([d['base'] for d in ret123 if d['base'] != '\n'])
        self.assertEqual(base_str, base)

        r123, e123 = Diff.diff(base, cmp1, cmp2, cmp3)
        self.assertEqual(len(r123), 20)
        base_str = ''.join([d['base'] for d in r123 if d['base'] != '\n'])
        self.assertEqual(base_str, base)

    def test_diff_lines(self):
        base_lines = """
        2.天地玄黄宇宙洪荒日月盈昃辰宿列张
        3.寒来暑往秋收冬藏闰余成岁律吕调阳
        4.云腾致雨露结为霜金生丽水玉出昆冈
        5.剑号巨阙珠称夜光果珍李柰菜重芥姜
        6.海咸河淡鳞潜羽翔龙师火帝鸟官人皇
        7.始制文字乃服衣裳推位让国有虞陶唐
        8.吊民伐罪周发殷汤坐朝问道垂拱平章
        9.爱育黎首臣伏戎羌遐迩一体率宾归王
        10.鸣凤在竹白驹食场化被草木赖及万方""".replace('        ', '')

        cmp_lines1 = """
        2.天地改黄宇增宙洪日月辰宿改张
        3.
        4.云腾致雨露结为霜金生丽水玉出昆冈
        5.剑号巨阙珠称夜光果珍李柰菜重芥姜始制文字乃服衣裳推位让国有虞陶唐
        6.海咸河淡鳞潜羽翔龙师火帝鸟官人皇
        7.始制文字乃服衣裳推位让国有虞陶唐女慕贞洁男效才良知过必改得能莫忘
        8.吊民伐罪周发殷汤坐朝问道垂拱平章
        9.爱育黎首臣伏戎羌遐迩一体率宾归王
        10.鸣凤在竹白驹食场化被草木赖及万方""".replace('        ', '')

        cmp_lines2 = """
        2.天地变黄宇加宙洪日月辰宿列变
        3.
        4.云腾致雨露结为霜金生丽水玉出昆冈
        5.剑号巨阙珠称夜光果珍李柰菜重芥姜始制文字乃服衣裳推位让国有虞陶唐
        6.海咸河淡鳞潜羽翔龙师火帝鸟官人皇
        7.始制文字乃服衣裳推位让国有虞陶唐
        8.吊民伐罪周发殷汤坐朝问道垂拱平章女慕贞洁男效才良知过必改得能莫忘
        9.爱育黎首臣伏戎羌遐迩一体率宾归王
        10.鸣凤在竹白驹食场化被草木赖及万方""".replace('        ', '')

        cmp_lines3 = """
        2.天地更黄宇附宙洪日月辰更列张
        3.
        4.云腾致雨露结为霜金生丽水玉出昆冈
        5.剑号巨阙珠称夜光果珍李柰菜重芥姜始制文字乃服衣裳推位让国有虞陶唐
        6.海咸河淡鳞潜羽翔龙师火帝鸟官人皇
        7.始制文字乃服衣裳推位让国有虞陶唐
        8.吊民伐罪周发殷汤坐朝问道垂拱平章
        9.爱育黎首臣伏戎羌遐迩一体率宾归王女慕贞洁男效才良知过必改得能莫忘
        10.鸣凤在竹白驹食场化被草木赖及万方""".replace('        ', '')

        ret1, err1 = Diff.diff(base_lines, cmp_lines1, label=dict(cmp1='cmp1'))
        self._assert_diff(ret1, base_lines, cmp_lines1)

        ret2, err2 = Diff.diff(base_lines, cmp_lines2, label=dict(cmp1='cmp2'))
        self._assert_diff(ret2, base_lines, cmp_lines2, label=dict(cmp1='cmp2'))

        ret3, err3 = Diff.diff(base_lines, cmp_lines3, label=dict(cmp1='cmp3'))
        self._assert_diff(ret3, base_lines, cmp_lines3, label=dict(cmp1='cmp3'))

        ret12, err12 = Diff._merge_by_combine(ret1, ret2)
        self._assert_diff(ret12, base_lines, cmp_lines1, cmp_lines2)

        r12, e12 = Diff.diff(base_lines, cmp_lines1, cmp_lines2)
        self._assert_diff(r12, base_lines, cmp_lines1, cmp_lines2)

        ret123, err12 = Diff._merge_by_combine(ret12, ret3)
        self._assert_diff(ret123, base_lines, cmp_lines1, cmp_lines2, cmp_lines3)

        r123, e123 = Diff.diff(base_lines, cmp_lines1, cmp_lines2, cmp_lines3)
        self._assert_diff(r123, base_lines, cmp_lines1, cmp_lines2, cmp_lines3)
