#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 页面工具
@time: 2019/6/3
"""
import re
from collections import Counter
from operator import itemgetter
from controller.page.diff import Diff
from tornado.escape import url_escape
from tornado.escape import json_decode
from controller.page.order import BoxOrder


class PageTool(BoxOrder):

    @staticmethod
    def decode_box(boxes):
        return json_decode(boxes) if isinstance(boxes, str) else boxes

    @classmethod
    def filter_box(cls, page, width, height):
        """ 过滤掉页面之外的切分框"""

        def valid(box):
            page_box = dict(x=2, y=2, w=width - 4, h=height - 4)
            is_valid = cls.box_overlap(box, page_box, True)
            if is_valid:
                box['x'] = 0 if box['x'] < 0 else box['x']
                box['y'] = 0 if box['y'] < 0 else box['y']
                box['w'] = width - box['x'] if box['x'] + box['w'] > width else box['w']
                box['h'] = height - box['h'] if box['y'] + box['h'] > height else box['h']
            return is_valid

        blocks = cls.decode_box(page['blocks'])
        columns = cls.decode_box(page['columns'])
        chars = cls.decode_box(page['chars'])
        blocks = [box for box in blocks if valid(box)]
        columns = [box for box in columns if valid(box)]
        chars = [box for box in chars if valid(box)]

        return blocks, columns, chars

    @classmethod
    def check_box_cover(cls, page, width=None, height=None):
        """ 检查页面字框覆盖情况"""

        def get_column_id(c):
            col_id = 'b%sc%s' % (c.get('block_no'), c.get('column_no'))
            return c.get('column_id') or re.sub(r'(c\d+)c\d+', r'\1', c.get('char_id', '')) or col_id

        width = width if width else page.get('width')
        height = height if height else page.get('height')
        blocks, columns, chars = cls.filter_box(page, width, height)
        char_out_block, char_in_block = cls.boxes_out_of_boxes(chars, blocks)
        if char_out_block:
            return False, '字框不在栏框内', [c['char_id'] for c in char_out_block]
        column_out_block, column_in_block = cls.boxes_out_of_boxes(columns, blocks)
        if column_out_block:
            return False, '列框不在栏框内', [get_column_id(c) for c in column_out_block]
        char_out_column, char_in_column = cls.boxes_out_of_boxes(chars, columns)
        if char_out_column:
            return False, '字框不在列框内', [c['char_id'] for c in char_out_column]
        return True, None, []

    @staticmethod
    def is_box_changed(page_a, page_b, ignore_none=True):
        """ 检查两个页面的切分信息是否发生了修改"""
        for field in ['blocks', 'columns', 'chars']:
            a, b = page_a.get(field), page_b.get(field)
            if ignore_none and (not a or not b):
                continue
            if len(a) != len(b):
                return field + '.len'
            for i in range(len(a)):
                for j in ['x', 'y', 'w', 'h']:
                    if abs(a[i][j] - b[i][j]) > 0.1 and (field != 'blocks' or len(a) > 1):
                        return '%s[%d] %s %f != %f' % (field, i, j, a[i][j], b[i][j])

    @classmethod
    def reorder_boxes(cls, chars=None, columns=None, blocks=None, page=None, direction=None):
        """ 针对页面的切分框重新排序"""
        if not chars and page:
            blocks = page.get('blocks') or []
            columns = page.get('columns') or []
            chars = page.get('chars') or []
        blocks = cls.calc_block_id(blocks)
        columns = cls.calc_column_id(columns, blocks)
        chars = cls.calc_char_id(chars, columns, small_direction=direction)
        return blocks, columns, chars

    @classmethod
    def adjust_blocks(cls, blocks, chars):
        """ 根据字框调整栏框边界，去掉没有字框的栏框"""
        ret = []
        for b in blocks:
            b_chars = [c for c in chars if c['block_no'] == b['block_no']]
            if b_chars:
                b.update(cls.get_outer_range(b_chars))
                ret.append(b)
        return ret

    @classmethod
    def adjust_columns(cls, columns, chars):
        """ 根据字框调整列框边界，去掉没有字框的列框"""
        ret = []
        for c in columns:
            c_chars = [ch for ch in chars if ch['block_no'] == c['block_no'] and ch['column_no'] == c['column_no']]
            if c_chars:
                c.update(cls.get_outer_range(c_chars))
                ret.append(c)
        return ret

    @classmethod
    def get_chars_col(cls, chars):
        """ 按照column_no对chars分组并设置cid。假定chars已排序"""
        ret = []
        assert chars, 'no chars in get_chars_col'
        cid_col = [chars[0]['cid']]
        for i, c in enumerate(chars[1:]):
            column_id1 = 'b%sc%s' % (c.get('block_no'), c.get('column_no'))
            column_id2 = 'b%sc%s' % (chars[i].get('block_no'), chars[i].get('column_no'))
            if column_id1 != column_id2:  # 换行
                ret.append(cid_col)
                cid_col = [c['cid']]
            else:
                cid_col.append(c['cid'])
        if cid_col:
            ret.append(cid_col)
        return ret

    @classmethod
    def merge_chars_col(cls, algorithm_chars_col, user_chars_col):
        """ 合并算法字序和用户校对字序。如果某一列二者cid不一致，则以算法字序为准，如果一致，则以用户字序为准"""
        ret = []
        len1 = len(algorithm_chars_col)
        len2 = len(user_chars_col)
        m_len = max([len1, len2])
        for i in range(m_len):
            while len(ret) <= i:
                ret.append([])
            cid1 = algorithm_chars_col[i] if i < len1 else []
            cid2 = user_chars_col[i] if i < len2 else []
            if set(cid1) == set(cid2):
                ret[i] = cid2
            else:
                ret[i] = cid1
        return ret

    @classmethod
    def cmp_cids(cls, chars, chars_col):
        cids1 = [c['cid'] for c in chars]
        cids2 = []
        for col_cid in chars_col:
            cids2.extend(col_cid)
        return set(cids1) == set(cids2)

    @classmethod
    def update_char_order(cls, chars, chars_col):
        """ 按照chars_col重排chars"""
        for col_cids in chars_col:
            col_chars = [c for c in chars if c['cid'] in col_cids]
            if not col_chars:
                continue
            cnt = Counter(['b%sc%s' % (c['block_no'], c['column_no']) for c in col_chars])
            column_id = cnt.most_common(1)[0][0]
            for char_no, cid in enumerate(col_cids):
                c = [c for c in col_chars if c['cid'] == cid][0]
                c['column_no'] = int(column_id[3:])
                c['char_no'] = char_no + 1
                c['char_id'] = 'b%sc%sc%s' % (c['block_no'], c['column_no'], c['char_no'])
        return sorted(chars, key=itemgetter('block_no', 'column_no', 'char_no'))

    @staticmethod
    def update_chars_cid(chars):
        updated = False
        max_cid = max([int(c.get('cid') or 0) for c in chars])
        for c in chars:
            if not c.get('cid'):
                c['cid'] = max_cid + 1
                max_cid += 1
                updated = True
        return updated

    @staticmethod
    def merge_narrow_columns(columns):
        """ 合并两个连续的窄列。假定columns已分栏并排好序"""
        if len(columns) < 3:
            return columns
        ws = sorted([c['w'] for c in columns], reverse=True)
        max_w = ws[0] * 1.1  # 合并后的宽度不超过max_w
        threshold = ws[2] * 0.6  # 窄列不超过threshold
        ret_columns = [columns[0]]
        for cur in columns[1:]:
            last = ret_columns[-1]
            w = last['x'] + last['w'] - cur['x']  # w为尝试合并成一个列的宽度
            b_cur, b_last = cur.get('block_no', 0), last.get('block_no', 0)
            if b_cur == b_last and w < max_w and cur['w'] < threshold and last['w'] < threshold:
                y = min([cur['y'], last['y']])
                h = max([cur['y'] + cur['h'], last['y'] + last['h']]) - y
                ret_columns[-1].update(dict(x=round(cur['x'], 2), y=round(y, 2), w=round(w, 2), h=round(h, 2)))
            else:
                ret_columns.append(cur)
        return ret_columns

    @classmethod
    def deduplicate_columns(cls, columns):
        """ 删除冗余的列。假定columns已分栏并排序"""
        if len(columns) < 3:
            return columns
        ws = sorted([c['w'] for c in columns], reverse=True)
        threshold = ws[2] * 0.6
        ret_columns = [columns[0]]
        for cur in columns[1:]:
            last = ret_columns[-1]
            overlap, ratio1, ratio2 = cls.box_overlap(last, cur)
            # 检查上一个字框，如果是窄框且重复度超过0.45，或者是大框且重复度超过0.55时，都将去除
            if (last['w'] < threshold and ratio1 > 0.45) or (last['w'] >= threshold and ratio1 > 0.55):
                ret_columns.pop()
            # 检查当前字框
            if (cur['w'] < threshold and ratio2 < 0.45) or (cur['w'] >= threshold and ratio2 < 0.55):
                ret_columns.append(cur)
        return ret_columns

    @classmethod
    def deduplicate_columns2(cls, columns):
        """ 删除冗余的列 """
        if len(columns) < 3:
            return columns
        ret_columns = sorted(columns, key=itemgetter('h'), reverse=True)
        for i, c in enumerate(ret_columns):
            for c2 in ret_columns[:i]:
                if c['w'] and cls.box_overlap(c, c2)[1] > 0.1:
                    c['w'] = 0
                    break
        return [c for c in ret_columns if c['w']]

    @classmethod
    def txt2html(cls, txt):
        """ 把文本转换为html，文本以空行或者||为分栏"""
        if re.match('<[a-z]+.*>.*</[a-z]+>', txt):
            return txt
        txt = '|'.join(txt) if isinstance(txt, list) else txt
        assert isinstance(txt, str)
        html, blocks = '', txt.split('||')
        line = '<li class="line"><span contenteditable="true" class="same" base="%s">%s</span></li>'
        for block in blocks:
            lines = block.split('|')
            html += '<ul class="block">%s</ul>' % ''.join([line % (l, l) for l in lines])
        return html

    @classmethod
    def html2txt(cls, html):
        """ 从html中获取txt文本，换行用|、换栏用||表示"""
        txt = ''
        html = re.sub('&nbsp;', '', html)
        regex1 = re.compile("<ul.*?>.*?</ul>", re.M | re.S)
        regex2 = re.compile("<li.*?>.*?</li>", re.M | re.S)
        regex3 = re.compile("<span.*?</span>", re.M | re.S)
        regex4 = re.compile("<span.*>(.*)</span>", re.M | re.S)
        for block in regex1.findall(html or ''):
            for line in regex2.findall(block or ''):
                if 'delete' not in line:
                    line_txt = ''
                    for span in regex3.findall(line or ''):
                        line_txt += ''.join(regex4.findall(span or ''))
                    txt += line_txt + '|'
            txt += '|'
        return re.sub(r'\|{2,}', '||', txt.rstrip('|'))

    @classmethod
    def get_ocr_txt(cls, boxes):
        """ 获取chars或columns里的ocr文本"""
        if not boxes:
            return ''
        pre, txt = boxes[0], ''
        for b in boxes[1:]:
            if pre.get('block_no') and b.get('block_no') and pre['block_no'] != b['block_no']:
                txt += '||'
            elif pre.get('line_no') and b.get('line_no') and pre['line_no'] != b['line_no']:
                txt += '|'
            txt += b.get('ocr_txt', '')
            pre = b
        return txt.strip('|')

    @classmethod
    def check_utf8mb4(cls, seg, base=None):
        column_strip = re.sub(r'\s', '', base or seg.get('base', ''))
        char_codes = [(c, url_escape(c)) for c in list(column_strip)]
        seg['utf8mb4'] = ','.join([c for c, es in char_codes if len(es) > 9])
        return seg

    @staticmethod
    def check_match(chars, txt):
        """ 检查图文是否匹配，包括总行数和每行字数"""
        # 获取每列字框数
        column_char_num = []
        if chars:
            pre, num = chars[0], 1
            for c in chars[1:]:
                if pre.get('block_no') and c.get('block_no') and pre['block_no'] != c['block_no']:  # 换栏
                    column_char_num.append(num)
                    num = 1
                elif pre.get('line_no') and c.get('line_no') and pre['line_no'] != c['line_no']:  # 换行
                    column_char_num.append(num)
                    num = 1
                else:
                    num += 1
            column_char_num.append(num)
        # 获取每行文字数
        txt_lines = re.sub(r'[\|\n]+', '|', txt).split('|')
        line_char_num = [len(line) for line in txt_lines]
        # 进行比对检查
        mis_match = []
        if len(column_char_num) < len(line_char_num):
            for i, num in enumerate(column_char_num):
                if num != line_char_num[i]:
                    mis_match.append([i, num, line_char_num[i]])
            for i in range(len(column_char_num), len(line_char_num)):
                mis_match.append([i, 0, line_char_num[i]])
        else:
            for i, num in enumerate(line_char_num):
                if num != column_char_num[i]:
                    mis_match.append([i, column_char_num[i], num])
            for i in range(len(line_char_num), len(column_char_num)):
                mis_match.append([i, column_char_num[i], 0])
        # 输出结果，r表示是否匹配，mis_match表示不匹配的情况
        r = len(column_char_num) == len(line_char_num) and not mis_match
        return r, mis_match, column_char_num, line_char_num

    @staticmethod
    def update_chars_txt(chars, txt):
        """ 将txt回写到chars中。假定图文匹配"""
        txt = re.sub(r'[\|\n]+', '', txt)
        if len(chars) != len(txt):
            return False
        for i, c in enumerate(chars):
            c['txt'] = txt[i]
        return chars

    @classmethod
    def diff(cls, base, cmp1='', cmp2='', cmp3=''):
        """ 生成文字校对的segment"""
        # 1. 生成segments
        segments = []
        pre_empty_line_no = 0
        block_no, line_no = 1, 1
        base = base.replace(' ', '')
        diff_segments = Diff.diff(base, cmp1, cmp2, cmp3)[0]
        for s in diff_segments:
            if s['is_same'] and s['base'] == '\n':  # 当前为空行，即换行
                if not pre_empty_line_no:  # 连续空行仅保留第一个
                    s['block_no'], s['line_no'] = block_no, line_no
                    segments.append(s)
                    line_no += 1
                pre_empty_line_no += 1
            else:  # 当前非空行
                if pre_empty_line_no > 1:  # 之前有多个空行，即换栏
                    line_no = 1
                    block_no += 1
                s['block_no'], s['line_no'] = block_no, line_no
                segments.append(s)
                pre_empty_line_no = 0
        # 2. 结构化，以便页面输出
        blocks = {}
        for s in segments:
            b_no, l_no = s['block_no'], s['line_no']
            if not blocks.get(b_no):
                blocks[b_no] = {}
            if not blocks[b_no].get(l_no):
                blocks[b_no][l_no] = []
            if s['is_same'] and s['base'] == '\n':  # 跳过空行
                continue
            if s['base'] in [' ', '\u3000'] and not s.get('cmp1') and not s.get('cmp2'):
                s['is_same'] = True
            s['offset'] = s['range'][0]
            blocks[b_no][l_no].append(s)
        return blocks
