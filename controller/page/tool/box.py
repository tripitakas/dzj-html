#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 字框工具
@time: 2019/6/3
"""
import re
from .order import BoxOrder
from collections import Counter
from operator import itemgetter
from tornado.escape import json_decode


class Box(BoxOrder):

    @staticmethod
    def decode_box(boxes):
        return json_decode(boxes) if isinstance(boxes, str) else boxes

    @classmethod
    def filter_box(cls, page, width, height):
        """ 过滤掉页面之外的切分框"""

        def valid(box):
            page_box = dict(x=0, y=0, w=width, h=height)
            is_valid = cls.box_overlap(box, page_box, True)
            if is_valid:
                box['x'] = 0 if box['x'] < 0 else box['x']
                box['y'] = 0 if box['y'] < 0 else box['y']
                box['w'] = width - box['x'] if box['x'] + box['w'] > width else box['w']
                box['h'] = height - box['h'] if box['y'] + box['h'] > height else box['h']
            return is_valid

        chars = cls.decode_box(page['chars'])
        blocks = cls.decode_box(page['blocks'])
        columns = cls.decode_box(page['columns'])
        chars = [box for box in chars if valid(box)]
        blocks = [box for box in blocks if valid(box)]
        columns = [box for box in columns if valid(box)]
        return blocks, columns, chars

    @classmethod
    def check_box_cover(cls, page, width=None, height=None):
        """ 检查页面字框覆盖情况"""
        width = width or page.get('width')
        height = height or page.get('height')
        blocks, columns, chars = cls.filter_box(page, width, height)
        char_out_column, char_in_column = cls.boxes_out_of_boxes(chars, columns)
        if char_out_column:
            return False, '字框不在列框内', 'char', [c['cid'] for c in char_out_column]
        char_out_block, char_in_block = cls.boxes_out_of_boxes(chars, blocks)
        if char_out_block:
            return False, '字框不在栏框内', 'char', [c['cid'] for c in char_out_block]
        column_out_block, column_in_block = cls.boxes_out_of_boxes(columns, blocks)
        if column_out_block:
            return False, '列框不在栏框内', 'column', [c['cid'] for c in column_out_block]
        return True, None, None, []

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
            if not b.get('deleted'):
                b_chars = [c for c in chars if c.get('block_no') and str(c['block_no']) == str(b['block_no'])]
                if b_chars:
                    b.update(cls.get_outer_range(b_chars))
                    ret.append(b)
            else:
                ret.append(b)
        return ret

    @classmethod
    def adjust_columns(cls, columns, chars):
        """ 根据字框调整列框边界，去掉没有字框的列框"""
        ret = []
        for c in columns:
            if not c.get('deleted'):
                c_chars = [ch for ch in chars if ch.get('block_no') and ch.get('column_no')
                           and str(ch['column_no']) == str(c.get('column_no'))
                           and str(ch['block_no']) == str(c.get('block_no'))]
                if c_chars:
                    c.update(cls.get_outer_range(c_chars))
                    ret.append(c)
            else:
                ret.append(c)
        return ret

    @classmethod
    def get_chars_col(cls, chars):
        """ 按照column_no对chars分组并设置cid。假定chars已排序"""
        if not chars:
            return []
        ret = []
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
    def cmp_char_cid(cls, chars, chars_col):
        cid1 = [c['cid'] for c in chars]
        cid2 = []
        for col_cid in chars_col:
            cid2.extend(col_cid)
        return set(cid1) == set(cid2)

    @classmethod
    def update_char_order(cls, chars, chars_col):
        """ 按照chars_col重排chars"""
        for col_cid in chars_col:
            col_chars = [c for c in chars if c['cid'] in col_cid]
            if not col_chars:
                continue
            cnt = Counter(['b%sc%s' % (c['block_no'], c['column_no']) for c in col_chars])
            column_id = cnt.most_common(1)[0][0]
            block_no, column_no = column_id[1:].split('c')
            for char_no, cid in enumerate(col_cid):
                c = [c for c in col_chars if c['cid'] == cid][0]
                c['block_no'] = int(block_no)
                c['column_no'] = int(column_no)
                c['char_no'] = char_no + 1
                c['char_id'] = 'b%sc%sc%s' % (c['block_no'], c['column_no'], c['char_no'])
        return sorted(chars, key=itemgetter('block_no', 'column_no', 'char_no'))

    @staticmethod
    def update_box_cid(boxes):
        updated = False
        if boxes:
            max_cid = max([int(c.get('cid') or 0) for c in boxes])
            for b in boxes:
                if not b.get('cid'):
                    b['cid'] = max_cid + 1
                    max_cid += 1
                    updated = True
        return updated

    @classmethod
    def update_page_cid(cls, page, box_types=None):
        updated = False
        box_types = box_types or ['blocks', 'columns', 'chars']
        for box_type in box_types:
            r = cls.update_box_cid(page.get(box_type))
            updated = updated or r
        return updated

    @staticmethod
    def is_box_pos_equal(box1, box2):
        for k in ['x', 'y', 'w', 'h']:
            if box1.get(k) != box2.get(k):
                return False
        return True

    @staticmethod
    def pack_box(box, fields):
        return {k: box.get(k) for k in fields}

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
