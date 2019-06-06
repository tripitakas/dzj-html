#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: diff类
@time: 2019/6/4
"""
import re
import math
from difflib import SequenceMatcher
from controller.variant import variants


class Diff(object):
    junk_str = r'[0-9a-zA-Z_「」\.\n\s\[\]\{\}，、：；。？！“”‘’@#￥%……&*（）]'

    @classmethod
    def find(cls, find, from_str, limit=1):
        # s = [m for m in process.extract(find, from_str, limit=limit)]
        # return s[0][0] if s else ''
        pass

    @classmethod
    def diff(cls, base='', cmp1='', cmp2='', cmp3='', check_variant=True, label=None):
        """
        文本比对，换行以base的换行为准，自动过滤掉cmp1/cmp2/cmp3的换行符
        :param base:
        :param cmp1:
        :param cmp2:
        :param cmp3:
        :param check_variant:
        :param label: {'base': '...', 'cmp1': '...', 'cmp2': '...', 'cmp3': '...'}
        :return:
        """
        lbl = {'base': 'base', 'cmp1': 'cmp1', 'cmp2': 'cmp2', 'cmp3': 'cmp3'}
        if label:
            lbl.update(label)
        base = Diff.pre_ocr(base)
        ret = Diff._diff(base, Diff.pre_cmp(cmp1), check_variant, {'base': lbl['base'], 'cmp': lbl['cmp1']})
        err = []
        if cmp2:
            ret2 = Diff._diff(base, Diff.pre_cmp(cmp2), check_variant, {'base': lbl['base'], 'cmp': lbl['cmp2']})
            ret, _err = Diff._merge_by_combine(ret, ret2, base_key=lbl['base'])
            err.extend(_err)
        if cmp3:
            ret3 = Diff._diff(base, Diff.pre_cmp(cmp3), check_variant, {'base': lbl['base'], 'cmp': lbl['cmp3']})
            ret, _err = Diff._merge_by_combine(ret, ret3, base_key=lbl['base'])
            err.extend(_err)
        return ret, err

    @classmethod
    def _diff(cls, base, cmp, check_variant=True, label=None):
        lbl = {'base': 'base', 'cmp': 'cmp'}
        if label:
            lbl.update(label)
        ret = []
        line_no = 1
        seg_no = 1
        s = SequenceMatcher(None, base, cmp)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            t1, t2 = base[i1:i2], cmp[j1:j2]
            # print('{:7}   a[{}:{}] --> b[{}:{}] {!r:>8} --> {!r}'.format(tag, i1, i2, j1, j2, t1, t2))
            if '\n' in t1:  # 换行符
                lst1 = t1.split('\n')
                for k, _t1 in enumerate(lst1):
                    if _t1 != '':
                        r = {'line_no': line_no, 'seg_no': seg_no, 'is_same': False, lbl['base']: _t1, lbl['cmp']: t2}
                        ret.append(r)
                        seg_no += 1
                        t2 = ''
                    elif k == len(lst1) - 1 and t2:
                        r = {'line_no': line_no, 'seg_no': seg_no, 'is_same': False, lbl['base']: _t1, lbl['cmp']: t2}
                        ret.append(r)
                        seg_no += 1
                    if k < len(lst1) - 1:
                        r = {'line_no': line_no, 'seg_no': seg_no, 'is_same': True, lbl['base']: '\n', lbl['cmp']: '\n'}
                        ret.append(r)
                        line_no += 1
                        seg_no = 1
            else:
                is_same = True if tag == 'equal' else False
                r = {'line_no': line_no, 'seg_no': seg_no, 'is_same': is_same, lbl['base']: t1, lbl['cmp']: t2}
                if check_variant and len(t1) == 1 and len(t2) == 1 and t1 != t2 and Diff.is_variant(t1, t2):
                    r['is_variant'] = True
                ret.append(r)
                seg_no += 1
        return ret

    @classmethod
    def _merge_by_combine(cls, d1, d2, base_key='base'):
        line_nos = list({d['line_no'] for d in d1})
        line_nos.sort()
        ret, err = [], []
        for line_no in line_nos:
            d1_cur_line = [d for d in d1 if d['line_no'] == line_no and d[base_key] != '\n']
            d2_cur_line = [d for d in d2 if d['line_no'] == line_no and d[base_key] != '\n']
            d1_cur_line_base_txt = [d[base_key] for d in d1_cur_line]
            d2_cur_line_base_txt = [d[base_key] for d in d2_cur_line]
            # 检查base_key对应的基础文本是否相同
            if ''.join(d1_cur_line_base_txt) != ''.join(d2_cur_line_base_txt):
                err.append(line_no)
                continue
            # d1异文的起止位置
            d2_diff_pos, s = [], 0
            for d in d2_cur_line:
                if not d['is_same']:
                    d2_diff_pos.append((s, s + len(d[base_key])))
                s += len(d[base_key])
            # d2异文的起止位置
            d1_diff_pos, s = [], 0
            for d in d1_cur_line:
                if not d['is_same']:
                    d1_diff_pos.append((s, s + len(d[base_key])))
                s += len(d[base_key])
            # 用diff_pos来分别改造d1和d2
            merge_pos = Diff._merge_diff_pos(d1_diff_pos, d2_diff_pos)
            _d1 = Diff._re_combine_one_line(d1_cur_line, merge_pos, base_key)
            _d2 = Diff._re_combine_one_line(d2_cur_line, merge_pos, base_key)
            # 合并d2至d1
            for i in range(0, len(_d1)):
                _d1[i].update(_d2[i])
            ret.extend(_d1)
        return ret, err

    @classmethod
    def _merge_diff_pos(cls, diff_pos1, diff_pos2):
        """合并两个异文的起止位置"""
        diff_pos = diff_pos1 + diff_pos2
        diff_pos.sort(key=lambda x: x[1])
        merge_pos, i, handled = [], 0, False
        while i < len(diff_pos):
            s, e = diff_pos[i]
            # 检查是否最后一个元素
            if i == len(diff_pos) - 1:
                merge_pos.append((s, e))
                break
            # 检查跟上一个元素（已入栈的最后一个元素）是否有交集
            if merge_pos:
                _s1, _e1 = merge_pos[-1]
                if s <= _e1:
                    merge_pos.pop()
                    merge_pos.append((_s1, e))
                    handled = True
            # 检查跟下一个元素是否有交集
            s1, e1 = diff_pos[i + 1]
            if e >= s1:
                if handled:
                    _s1, _e1 = merge_pos[-1]
                    merge_pos.pop()
                    merge_pos.append((_s1, e1))
                else:
                    merge_pos.append((s, e1))
                i += 1  # 跳过下一个元素
            else:
                if not handled:
                    merge_pos.append((s, e))
            # 设置下一次处理的标志
            i += 1
            handled = False
        return merge_pos

    @classmethod
    def _re_combine_one_line(cls, diff, diff_pos, base_key='base'):
        """
        diff是一行文本的比对结果，diff_pos是异文段的区间集合，要求diff按照diff_pos重新改造。 diff中的异文相对于整行文本来讲，也有
        它对应的异文段区间集合，假设为diff_pos1。由于diff_pos是diff_pos1和其它异文段区间合并的结果，因此diff_pos1应该是diff_pos
        的子集。
        :param diff [{'is_same': True, 'base': '一二三', 'txt1': '一二三'}, ...] 一行文本的diff结果
        :param diff_pos [(s1, e1), (s2, e2), (s3, e3)...]，其中(s, e)代表异文的起止位置（左闭右开）。
        """
        ret, idx = [], 0
        s1, e1 = 0, 0  # diff中当前元素在整行文本中的起止位置
        for s, e in diff_pos:
            completed = False  # 当前(s, e)是否已处理完
            while idx < len(diff) and not completed:
                d = diff[idx]
                e1 = s1 + len(d[base_key])
                if e1 <= s:  # (s1, e1)在(s, e)的左边
                    ret.append(d)
                    # 设置后续处理
                    if e1 == s == e:  # 这种情况是比对本相对base新增了文本，例如{'base': '', 'txt1': '增'}
                        completed = True
                    idx += 1
                    s1 = e1
                elif s1 < s <= e1 <= e:  # (s1, e1)左交于(s, e)
                    if d['is_same']:  # d为同文
                        sub1 = {k: (v[0: s - s1] if isinstance(v, str) else v) for k, v in d.items()}
                        ret.append(sub1)
                        sub2 = {k: (v[s - s1:] if isinstance(v, str) else v) for k, v in d.items()}
                        sub2['is_same'] = False
                        ret.append(sub2)
                        if e1 == e:
                            completed = True
                    else:  # d为异文
                        ret.append(d)
                    # 设置后续处理
                    idx += 1
                    s = s1 = e1
                elif s1 < s <= e < e1:  # (s1, e1)包围(s, e)
                    assert d['is_same']  # d应为同文
                    sub1 = {k: (v[0: s - s1] if isinstance(v, str) else v) for k, v in d.items()}
                    ret.append(sub1)
                    sub2 = {k: (v[s - s1: e - s1] if isinstance(v, str) else v) for k, v in d.items()}
                    sub2['is_same'] = False
                    ret.append(sub2)
                    # 设置后续处理
                    diff[idx] = {k: (v[e - s1: e1 - s1] if isinstance(v, str) else v) for k, v in d.items()}
                    completed = True
                    s1 = e
                elif s <= s1 < e1 <= e:  # (s, e)包围或等于(s1, e1)
                    d['is_same'] = False
                    ret.append(d)
                    # 设置后续处理
                    if e1 == e:
                        completed = True
                    s = s1 = e1
                    idx += 1
                elif s <= s1 < e < e1:  # (s1, e1)右交于(s, e)
                    assert d['is_same']  # d应为同文
                    sub1 = {k: (v[0: e - s1] if isinstance(v, str) else v) for k, v in d.items()}
                    sub1['is_same'] = False
                    ret.append(sub1)
                    # 设置后续处理
                    diff[idx] = {k: (v[e - s1:] if isinstance(v, str) else v) for k, v in d.items()}
                    completed = True
                    s1 = e

        # 处理剩下的diff
        while idx < len(diff):
            ret.append(diff[idx])
            idx += 1

        # 合并前后相接的同文或异文
        _ret, seg_no = [], 1
        for r in ret:
            if _ret and r['is_same'] == _ret[-1]['is_same']:
                _r = _ret.pop()
                seg_no -= 1
                r = {k: (_r.get(k) + v if isinstance(v, str) else v) for k, v in r.items()}
            r['seg_no'] = seg_no
            _ret.append(r)
            seg_no += 1

        return _ret

    @classmethod
    def _merge_by_split(cls, d1, d2, base_key='base'):
        """
        合并diff的比对结果。针对d1中相同line_no的记录，其base_key所对应的值合并起来是一行文本，和d2中相同line_no的记录base_key所
        对应的指合并起来的文本相同。
        :param d1: base和txt1比对的结果
        :param d2: base和txt2比对的结果
        :param base_key: d1，d2中base所对应的field
        :return:
        """
        line_nos = list({d['line_no'] for d in d1})
        line_nos.sort()
        ret, err = [], []
        for line_no in line_nos:
            d1_cur_line = [d for d in d1 if d['line_no'] == line_no and d[base_key] != '\n']
            d2_cur_line = [d for d in d2 if d['line_no'] == line_no and d[base_key] != '\n']
            d1_cur_line_base_txt = [d[base_key] for d in d1_cur_line]
            d2_cur_line_base_txt = [d[base_key] for d in d2_cur_line]
            # 检查base_key对应的基础文本是否相同
            if ''.join(d1_cur_line_base_txt) != ''.join(d2_cur_line_base_txt):
                err.append(line_no)
                continue
            # 用d2的位置重新分割d1
            d2_cur_pos = [len(d) for d in d2_cur_line_base_txt]
            _d1 = Diff._re_split_one_line(d1_cur_line, d2_cur_pos, base_key)
            # 用d1的位置重新分割d2
            d1_cur_pos = [len(d) for d in d1_cur_line_base_txt]
            _d2 = Diff._re_split_one_line(d2_cur_line, d1_cur_pos, base_key)
            # 合并d2至d1
            for i in range(0, len(_d1)):
                _d1[i].update(_d2[i])
            ret.extend(_d1)
        return ret, err

    @classmethod
    def _re_split_one_line(cls, d1, d2_pos, base_key):
        """d1代表base和txt1的比对结果，d2代表base和txt2的比对结果，base中的一行文本被txt1和txt2分割成了不同的文本段。
        将d2的分割方式合并到d1中，取得最短异文段落，返回重新分割后的结果。"""
        ret, d1_start, seg_no = [], 0, 0
        for d in d1:
            d1_end = d1_start + len(d[base_key]) - 1
            d2_pos_lt_d = [p for p in d2_pos if d1_start <= p < d1_end]
            d2_pos_lt_d = [p - d1_start for p in d2_pos_lt_d]
            d1_start += len(d[base_key])
            if not d2_pos_lt_d:
                ret.append(d)
                continue
            d2_split, d2_start = [], 0
            for p in d2_pos_lt_d:
                d2_split.append((d2_start, p + 1))
                d2_start = p + 1
            d2_split.append((d2_start, len(d[base_key])))

            for s, e in d2_split:
                _d = {}
                for k, v in d.items():
                    # 按比例拆分字符串
                    if v and type(v) == str:
                        _d[k] = Diff._get_sub_by_ratio(v, s, e, len(d[base_key]))
                    else:
                        _d[k] = v
                seg_no += 1
                _d['seg_no'] = seg_no
                ret.append(_d)
        return ret

    @classmethod
    def _get_sub_by_ratio(cls, from_str, start, end, length):
        s = math.ceil((start + 1) / length * len(from_str)) - 1
        e = math.ceil((end + 1) / length * len(from_str)) - 1
        return from_str[s: e]

    @classmethod
    def pre_ocr(cls, ocr):
        """OCR预处理"""
        return ocr

    @classmethod
    def pre_cmp(cls, cmp):
        """比对本预处理，过滤其中的非中文字符"""
        return re.sub(Diff.junk_str, '', cmp)

    @classmethod
    def is_variant(cls, a, b):
        """检查a和b是否为异体字关系"""
        assert len(a) == 1 and len(b) == 1
        variants_str = r'#%s#' % '#'.join(variants)
        m = re.search(r'#[^#]*%s[^#]*#' % a, variants_str)
        return True if a != b and m and b in m.group(0) else False
