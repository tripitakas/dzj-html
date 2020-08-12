#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: diff类
@time: 2019/6/4
"""
import re
from .variant import is_variant

try:
    from cdifflib import CSequenceMatcher
except ImportError:
    # Windows上跳过安装cdifflib
    def CSequenceMatcher(is_junk, a, b, auto_junk):
        return [is_junk, a, b, auto_junk] and []


class Diff(object):
    # YMN*等是校对符号，不要去掉
    base_junk_char = r'[\-\.\{\}\(\),0-9a-z_「」『』（）〈〉《》|，、：；。？！“”‘’—#Ω￥%&*◎…]'
    cmp_junk_char = r'[\-\.\{\}\(\),0-9a-z_「」『』（）〈〉《》|，、：；。？！“”‘’—#Ω￥%&*◎…\s\n\f\t\v\u3000]'

    @classmethod
    def pre_base(cls, base, keep_line=True):
        """ base预处理"""
        # 平台中用|表示换行，因此先恢复换行
        base = base.replace('|', '\n').rstrip('\n')
        # 根据参数决定是否保留换行
        base = base.replace('\n', '') if not keep_line else base
        return re.sub(Diff.base_junk_char, '', base)

    @classmethod
    def pre_cmp(cls, cmp):
        """ 比对本预处理，过滤换行符以及非中文字符"""
        return re.sub(Diff.cmp_junk_char, '', cmp)

    @classmethod
    def diff(cls, base='', cmp1='', cmp2='', cmp3='', check_variant=True, label=None):
        """ 文本比对。 换行以base的换行为准，自动过滤掉cmp1/cmp2/cmp3的换行符
        :param base: 基础比对文本
        :param check_variant: 是否检查异体字
        :param label: {'base': '...', 'cmp1': '...', 'cmp2': '...', 'cmp3': '...'}
        """
        lbl = {'base': 'base', 'cmp1': 'cmp1', 'cmp2': 'cmp2', 'cmp3': 'cmp3'}
        if label and isinstance(label, dict):
            lbl.update(label)

        base = base or ''
        if not cmp1 and not cmp2 and not cmp3:
            return Diff._diff_one(base), []

        ret, err = [], []
        diff_func = Diff._diff_two_v2
        if cmp1:
            ret1 = diff_func(base, cmp1, check_variant, {'base': lbl['base'], 'cmp': lbl['cmp1']})
            ret, _err = Diff._merge_by_combine(ret, ret1, base_key=lbl['base'])
            err.extend(_err)
        if cmp2:
            ret2 = diff_func(base, cmp2, check_variant, {'base': lbl['base'], 'cmp': lbl['cmp2']})
            ret, _err = Diff._merge_by_combine(ret, ret2, base_key=lbl['base'])
            err.extend(_err)
        if cmp3:
            ret3 = diff_func(base, cmp3, check_variant, {'base': lbl['base'], 'cmp': lbl['cmp3']})
            ret, _err = Diff._merge_by_combine(ret, ret3, base_key=lbl['base'])
            err.extend(_err)
        return ret, err

    @classmethod
    def _diff_one(cls, base):
        """ 将单独一份文本按照_diff_two的格式输出"""
        base = Diff.pre_base(base)
        ret, line_no = [], 1
        for line in base.split('\n'):
            if line:
                ret.append({'line_no': line_no, 'is_same': True, 'base': line})
            ret.append({'line_no': line_no, 'is_same': True, 'base': '\n'})
            line_no += 1

        line_no, start = 1, 0
        for r in ret:
            if r['line_no'] != line_no:  # 换行
                line_no += 1
                start = 0
            end = start + len(r['base'])
            r['range'] = (start, end)
            start = end
        return ret

    @classmethod
    def _diff_two_v2(cls, base, cmp, check_variant=True, label=None):
        lbl = {'base': 'base', 'cmp': 'cmp'}
        if label and isinstance(label, dict):
            lbl.update(label)

        # 和v1不同，v2在比较时，先去掉换行符，以免对diff算法干扰
        base = base.replace('|', '\n').rstrip('\n')
        base_lines = base.split('\n')
        base = cls.pre_base(base, False)
        cmp = cls.pre_cmp(cmp)
        segments = []
        s = CSequenceMatcher(None, base, cmp, autojunk=False)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            t1, t2 = base[i1:i2], cmp[j1:j2]
            # print('{:7}   a[{}:{}] --> b[{}:{}] {!r:>8} --> {!r}'.format(tag, i1, i2, j1, j2, t1, t2))
            is_same = True if tag == 'equal' else False
            r = {'line_no': None, 'is_same': is_same, lbl['base']: t1, lbl['cmp']: t2}
            if check_variant and len(t1) == 1 and len(t2) == 1 and t1 != t2 and is_variant(t1, t2):
                r['is_variant'] = True
                r['is_same'] = True
            segments.append(r)

        # 合并diff时可能被异体字隔断的同文
        for i, seg in enumerate(segments):
            if seg.get('is_same'):
                # 往前找一个没有被delete的同文seg进行合并
                j = i - 1
                while j >= 0:
                    pre = segments[j]
                    if not pre['is_same']:
                        break
                    if not pre.get('deleted'):
                        pre[lbl['base']] += seg[lbl['base']]
                        pre[lbl['cmp']] += seg[lbl['cmp']]
                        seg['deleted'] = True
                        break
                    j -= 1
        segments = [s for s in segments if not s.get('deleted')]

        # 根据diff比较的结果，按照base设置换行
        line_segments, idx = [], 0
        for i, line in enumerate(base_lines):
            if not len(line):  # 如果line为空，则新增换行
                line_segments.append({'line_no': i + 1, 'is_same': True, lbl['base']: '\n', lbl['cmp']: '\n'})
                continue
            # 从segments中找len(line)长作为第i+1行
            start, left_len = 0, len(line)
            while idx < len(segments) and left_len > 0:
                seg = segments[idx]
                if len(seg[lbl['base']]) <= left_len:  # seg比left_len短，seg入栈
                    seg['line_no'] = i + 1
                    seg_len = len(seg[lbl['base']])
                    line_segments.append(seg)
                    # 更新变量
                    left_len -= seg_len
                    start += seg_len
                    idx += 1
                else:  # seg比left_len长，截断seg
                    front_part = {
                        'line_no': i + 1, 'is_same': seg['is_same'], lbl['base']: seg[lbl['base']][:left_len],
                        lbl['cmp']: seg[lbl['cmp']][:left_len],
                    }
                    line_segments.append(front_part)
                    seg.update({
                        lbl['cmp']: seg[lbl['cmp']][left_len:] if len(seg[lbl['cmp']]) > left_len else '',
                        lbl['base']: seg[lbl['base']][left_len:],
                    })
                    # 更新变量
                    left_len = 0
                    start = 0

                if left_len == 0:  # 换行
                    line_segments.append({'line_no': i + 1, 'is_same': True, lbl['base']: '\n', lbl['cmp']: '\n'})

        # 检查换行符后是否有base为空的异文，有则往前提
        for i, seg in enumerate(line_segments):
            pre = line_segments[i - 1] if i > 1 else {}
            if seg[lbl['base']] == '' and pre.get('is_same') and pre.get(lbl['base']) == '\n':
                # 当前为空异文，之前为换行，则交换二者位置
                seg['line_no'] = pre['line_no']
                line_segments[i - 1] = seg
                line_segments[i] = pre

        # 设置range
        start = 0
        for seg in line_segments:
            seg['range'] = (start, start + len(seg[lbl['base']]))
            start += len(seg[lbl['base']])
            if seg['is_same'] and seg[lbl['base']] == '\n':
                start = 0
        if line_segments[-1]['is_same'] and line_segments[-1][lbl['base']] == '\n':
            line_segments.pop()
        return line_segments

    @classmethod
    def _diff_two_v1(cls, base, cmp, check_variant=True, label=None):
        lbl = {'base': 'base', 'cmp': 'cmp'}
        if label and isinstance(label, dict):
            lbl.update(label)

        ret, line_no = [], 1
        base, cmp = cls.pre_base(base), cls.pre_cmp(cmp)
        s = CSequenceMatcher(None, base, cmp, autojunk=False)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            t1, t2 = base[i1:i2], cmp[j1:j2]
            # print('{:7}   a[{}:{}] --> b[{}:{}] {!r:>8} --> {!r}'.format(tag, i1, i2, j1, j2, t1, t2))
            if '\n' in t1:  # 换行符
                lst1 = t1.split('\n')
                for k, _t1 in enumerate(lst1):
                    if _t1 != '':
                        ret.append({'line_no': line_no, 'is_same': False, lbl['base']: _t1, lbl['cmp']: t2})
                        t2 = ''
                    elif k == len(lst1) - 1 and t2:
                        ret.append({'line_no': line_no, 'is_same': False, lbl['base']: _t1, lbl['cmp']: t2})
                    if k < len(lst1) - 1:  # 换行
                        ret.append({'line_no': line_no, 'is_same': True, lbl['base']: '\n'})
                        line_no += 1
            else:
                is_same = True if tag == 'equal' else False
                r = {'line_no': line_no, 'is_same': is_same, lbl['base']: t1, lbl['cmp']: t2}
                if check_variant and len(t1) == 1 and len(t2) == 1 and t1 != t2 and is_variant(t1, t2):
                    r['is_variant'] = True
                ret.append(r)

        # 设置起止位置
        line_no, start = 1, 0
        for r in ret:
            if r['line_no'] != line_no:  # 换行
                line_no += 1
                start = 0
            end = start + len(r[lbl['base']])
            r['range'] = (start, end)
            start = end

        return ret

    @classmethod
    def _merge_by_combine(cls, d1, d2, base_key='base'):
        if not d1 or not d2:
            return d1 or d2, []

        ret, err = [], []
        line_nos = sorted(list(set(d['line_no'] for d in d1)))
        for line_no in line_nos:
            line1 = [d for d in d1 if d['line_no'] == line_no and d[base_key] != '\n']
            line2 = [d for d in d2 if d['line_no'] == line_no and d[base_key] != '\n']
            base_txt1 = [d[base_key] for d in line1]
            base_txt2 = [d[base_key] for d in line2]
            # 检查base_key对应的基础文本是否相同
            if ''.join(base_txt1) != ''.join(base_txt2):
                err.append(line_no)
                continue
            # 用merge_pos来分别改造d1和d2，使得二者分割方式一致
            d1_diff_pos = [d['range'] for d in line1 if not d['is_same']]
            d2_diff_pos = [d['range'] for d in line2 if not d['is_same']]
            merge_pos = Diff._merge_diff_pos(d1_diff_pos, d2_diff_pos)
            _line1 = Diff._reorganize_line(line1, merge_pos, base_key)
            _line2 = Diff._reorganize_line(line2, merge_pos, base_key)
            # 合并二者，得到line_no行对应的最终结果
            for i in range(0, len(_line1)):
                if i < len(_line2):
                    _line1[i].update(_line2[i])
            _line1.append({'line_no': line_no, 'is_same': True, base_key: '\n'})
            # 将该行插入ret
            ret.extend(_line1)
        return ret, err

    @classmethod
    def _merge_diff_pos(cls, diff_pos1, diff_pos2):
        """ 合并两个异文的起止位置。有两种情况：一种是字位置，比如删除或修改一或多个字，起止位置(s, e)代表这段异文在整行文本中的位置。
        一种是点位置，比如在某个字后面，起止位置(s, e)中，s等于e，表示在这个字之后增加字。
        """
        diff_pos = list(set(diff_pos1 + diff_pos2))  # 去重
        diff_pos.sort(key=lambda x: x[0])  # 排序
        merge_pos = []
        for s, e in diff_pos:
            if s == e:  # 点位置
                if not merge_pos or (merge_pos and s >= merge_pos[-1][1]):
                    merge_pos.append((s, e))
            else:  # 字位置
                if merge_pos:
                    _s, _e = merge_pos[-1]
                    # assert _s <= s
                    if _e < s:  # 没有交集，直接插入
                        merge_pos.append((s, e))
                    else:  # 有交集，弹出最后一个元素，插入二者并集
                        merge_pos.pop()
                        merge_pos.append((_s, e if e > _e else _e))
                else:
                    merge_pos.append((s, e))
        return merge_pos

    @classmethod
    def _reorganize_line(cls, diff, diff_pos, base_key='base'):
        """
        diff是一行文本的比对结果集合，diff_pos是异文段的起止位置集合，要求按照diff_pos重新改造diff。 diff中异文段的起止位置集合
        diff_pos1，应该是diff_pos的子集。也就是说，diff_pos1中每一个元素对应的区间应在diff_pos的区间内。
        函数逻辑：针对diff_pos的每一项，从diff中找到对应的文本，设置为异文。
        :param diff [{'is_same': True, 'base': '一二三', 'txt1': '一二三', 'range': (0, 3)}, ...]
            针对base和cmp1中，一行文本比对结果
        :param diff_pos [(s1, e1), (s2, e2), (s3, e3)...]，其中(s, e)代表异文的起止位置（左闭右开）。
        """
        ret, idx = [], 0
        for s, e in diff_pos:
            completed = False  # 当前(s, e)是否已处理完
            while idx < len(diff) and not completed:
                _d = diff[idx]
                _s, _e = _d['range']
                if _s <= s:
                    if _e <= s:  # (_s, _e)在(s, e)的左边
                        ret.append(_d)
                        # 设置后续处理
                        completed = _e == e
                        idx += 1
                    elif s < _e <= e:  # (_s, _e)左交于(s, e)
                        if _s < s:
                            sub1 = {k: (v[0: s - _s] if isinstance(v, str) else v) for k, v in _d.items()}
                            ret.append(sub1)
                        sub2 = {k: (v[s - _s:] if isinstance(v, str) else v) for k, v in _d.items()}
                        sub2['is_same'] = False
                        ret.append(sub2)
                        # 设置后续处理
                        completed = _e == e
                        idx += 1
                        s = _e
                    elif e < _e:  # (_s, _e)包围(s, e)
                        # assert _d['is_same']  # d应为同文
                        if _s < s:
                            sub1 = {k: (v[0: s - _s] if isinstance(v, str) else v) for k, v in _d.items()}
                            ret.append(sub1)
                        sub2 = {k: (v[s - _s: e - _s] if isinstance(v, str) else v) for k, v in _d.items()}
                        sub2['is_same'] = False
                        ret.append(sub2)
                        # 设置后续处理
                        diff[idx] = {k: (v[e - _s: _e - _s] if isinstance(v, str) else v) for k, v in _d.items()}
                        diff[idx]['range'] = (e, _e)
                        completed = True
                elif s < _s:
                    if _e <= e:  # (s, e)包围(_s, _e)
                        _d['is_same'] = False
                        ret.append(_d)
                        # 设置后续处理
                        completed = _e == e
                        s = _e
                        idx += 1
                    elif e < _e:  # (_s, _e)右交于(s, e)
                        # assert _d['is_same']  # d应为同文
                        sub1 = {k: (v[0: e - _s] if isinstance(v, str) else v) for k, v in _d.items()}
                        sub1['is_same'] = False
                        ret.append(sub1)
                        # 设置后续处理
                        diff[idx] = {k: (v[e - _s:] if isinstance(v, str) else v) for k, v in _d.items()}
                        diff[idx]['range'] = (e, _e)
                        completed = True

        # 合并剩下的diff
        ret.extend(diff[idx:])

        # 合并前后相接的同文或异文，重新设置range
        _ret, start = [], 0
        for r in ret:
            if _ret and r['is_same'] == _ret[-1]['is_same']:  # 合并上一条同文或异文
                _r = _ret.pop()
                start -= len(_r[base_key])
                r = {k: (_r.get(k) + v if isinstance(v, str) else v) for k, v in r.items()}
            r['range'] = (start, start + len(r[base_key]))
            _ret.append(r)
            start += len(r[base_key])

        return _ret
