#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/6/3
"""
from .sort_v1 import calc as calc_old
from .sort_v2 import calc as calc_new
from functools import cmp_to_key
from operator import itemgetter
import re


class Sort(object):
    @classmethod
    def sort(cls, chars, columns, blocks, layout_type=None, chars_col=None):
        def init_id():
            max_id = max([c.get('id', 0) for c in chars]) if chars else 0
            for c in chars:
                if not c.get('id'):
                    max_id += 1
                    c['id'] = max_id

        def find_by_id(id_):
            return ([c for c in chars if c['id'] == id_] + [None])[0]

        zero_char_id = []
        if not chars_col:
            if cls.get_invalid_char_ids(chars):
                zero_char_id, layout_type = cls.sort_chars(chars, columns, blocks, layout_type)
            chars.sort(key=itemgetter('block_no', 'line_no', 'no'))
            init_id()
            col_ids = sorted(list(set([c['block_no'] * 100 + c['line_no'] for c in chars])))
            chars_col = [[c['id'] for c in chars if c['block_no'] * 100 + c['line_no'] == col_id]
                         for col_id in col_ids]
        else:
            assert blocks
            col_ids, indexes = {}, set()
            init_id()
            for char_ids in chars_col:
                for i, cid in enumerate(char_ids):
                    c = find_by_id(cid)
                    if not c:
                        # raise IndexError('字序越界(%d)' % cid)
                        continue
                    if i == 0:
                        block_no = c.get('block_no') or cls.get_block_index(c, blocks) + 1
                        line_no = col_ids[block_no] = col_ids.get(block_no, 0) + 1
                    c['block_no'] = block_no
                    c['line_no'] = line_no
                    c['char_no'] = c['no'] = i + 1
                    c['char_id'] = 'b%dc%dc%d' % (block_no, line_no, c['no'])
                    indexes.add(cid)
            # assert len(indexes) == len(chars)
        return zero_char_id, layout_type, chars_col

    @staticmethod
    def sort_blocks(blocks):
        """根据坐标对栏框排序和生成编号"""
        blocks.sort(key=cmp_to_key(lambda a, b: a['y'] + a['h'] / 2 - b['y'] - b['h'] / 2))
        for i, blk in enumerate(blocks):
            blk['no'] = i + 1
            blk['block_id'] = 'b%d' % blk['no']
        return blocks

    @staticmethod
    def get_block_index(column, blocks):
        index, dist = -1, 1e5
        for idx, blk in enumerate(blocks):
            d = abs(column['y'] + column['h'] / 2 - blk['y'] - blk['h'] / 2)
            if dist > d:
                dist = d
                index = idx
        return index

    @classmethod
    def sort_columns(cls, columns, blocks):
        """根据列框坐标和所在的栏对列框排序和生成编号"""
        columns_dict = [[] for _ in blocks]
        for c in columns:
            block_no = cls.get_block_index(c, blocks) + 1
            columns_dict[block_no - 1].append(c)

        ret_columns = []
        for blk_i, columns_blk in enumerate(columns_dict):
            columns_blk.sort(key=cmp_to_key(lambda a, b: b['x'] + b['w'] / 2 - a['x'] - a['w'] / 2))
            for i, c in enumerate(columns_blk):
                c['no'] = i + 1
                c['column_id'] = 'b%dc%d' % (blk_i + 1, c['no'])
            ret_columns.extend(columns_blk)

        return ret_columns

    @staticmethod
    def get_invalid_char_ids(chars):
        return [c.get('char_id') for c in chars if not (re.match(r'^b\dc\d+c\d{1,2}$', c.get('char_id', ''))
                                                        and c.get('block_no') and c.get('line_no') and c.get('no'))]

    @classmethod
    def sort_chars(cls, chars, columns, blocks, layout_type=None):
        """根据坐标对字框排序和生成编号"""
        if not layout_type:
            zero_char_id, layout_type = cls.sort_chars(chars, columns, blocks, 2)
            if zero_char_id:
                zero_char_id2, layout_type = cls.sort_chars(chars, columns, blocks, 1)
                if len(zero_char_id2) < len(zero_char_id):
                    zero_char_id = zero_char_id2
                else:
                    zero_char_id, layout_type = cls.sort_chars(chars, columns, blocks, 2)
        else:
            ids0 = {}
            new_chars = (calc_new if layout_type == 2 else calc_old)(chars, blocks, columns)
            assert len(new_chars) == len(chars)
            for c_i, c in enumerate(new_chars):
                if not c['column_order']:
                    zero_key = 'b%dc%d' % (c['block_id'], c['column_id'])
                    ids0[zero_key] = ids0.get(zero_key, 100) + 1
                    c['column_order'] = ids0[zero_key]
                chars[c_i]['char_id'] = 'b%dc%dc%d' % (c['block_id'], c['column_id'], c['column_order'])
                chars[c_i]['block_no'] = c['block_id']
                chars[c_i]['line_no'] = c['column_id']
                chars[c_i]['char_no'] = chars[c_i]['no'] = c['column_order']
            zero_char_id = cls.get_invalid_char_ids(chars)

        return zero_char_id, layout_type
