#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/6/3
"""
import re
import math
from operator import itemgetter
from functools import cmp_to_key
from .v1 import calc as calc_old
from .v2 import calc as calc_new


class CutTool(object):
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
        """ 根据坐标对栏框排序和生成编号(block_id,block_no,no)"""
        blocks.sort(key=cmp_to_key(lambda a, b: a['y'] + a['h'] / 2 - b['y'] - b['h'] / 2))
        for i, blk in enumerate(blocks):
            blk['no'] = blk['block_no'] = i + 1
            blk['block_id'] = 'b%d' % blk['no']
        return blocks

    @staticmethod
    def get_block_index(column, blocks):
        """根据列框坐标查找所在的栏序号"""
        index, dist = 0, 1e5  # 0表示默认属于第一栏，防止单栏列高度太大找不到栏
        for idx, blk in enumerate(blocks):  # 假定栏是上下分离的，只需要比较框中心Y的偏差
            d = math.hypot(column['x'] + column['w'] / 2 - blk['x'] - blk['w'] / 2,
                           column['y'] + column['h'] / 2 - blk['y'] - blk['h'] / 2)
            if dist > d:
                dist = d
                index = idx
        return index

    @classmethod
    def sort_columns(cls, columns, blocks):
        """ 根据列框坐标和所在的栏对列框排序和生成编号(column_id,line_no,no)"""

        # 根据坐标将列分组到各栏
        columns_dict = [[] for _ in blocks]
        for c in columns:
            block_index = cls.get_block_index(c, blocks)
            columns_dict[block_index].append(c)

        ret_columns = []
        for blk_i, columns_blk in enumerate(columns_dict):
            # 在一栏内，按水平坐标对其列排序
            columns_blk.sort(key=cmp_to_key(lambda a, b: b['x'] + b['w'] / 2 - a['x'] - a['w'] / 2))
            for i, c in enumerate(columns_blk):
                c['no'] = c['line_no'] = i + 1
                c['column_id'] = 'b%dc%d' % (blocks[blk_i].get('block_no', blk_i + 1), c['no'])
            ret_columns.extend(columns_blk)

        return ret_columns

    @staticmethod
    def get_invalid_char_ids(chars):
        def valid(c):
            regex = r'^b\dc\d+c\d{1,2}$'
            return re.match(regex, c.get('char_id', '')) and c.get('block_no') and c.get('line_no') and c.get('no')

        return [c.get('char_id') for c in chars if not valid(c)]

    @classmethod
    def sort_chars(cls, chars, columns, blocks, layout_type=None):
        """根据坐标对字框排序和生成编号, layout_type: 0-智能选择（在外层调用处为0时已取页面原字序类型）, 1-旧算法, 2-新算法"""
        if not layout_type:
            zero_char_id, layout_type = cls.sort_chars(chars, columns, blocks, 2)  # 先用新算法
            if zero_char_id:
                zero_char_id2, layout_type = cls.sort_chars(chars, columns, blocks, 1)  # 再试旧算法
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

    @classmethod
    def char_render(cls, page, layout, **kwargs):
        """ 生成字序编号 """
        need_ren = CutTool.get_invalid_char_ids(page['chars']) or layout and layout != page.get('layout_type')
        if need_ren:
            page['chars'][0]['char_id'] = ''  # 强制重新生成编号
        kwargs['zero_char_id'], page['layout_type'], kwargs['chars_col'] = CutTool.sort(
            page['chars'], page['columns'], page['blocks'], layout or page.get('layout_type'))
        return kwargs

    @staticmethod
    def calc(blocks, columns, chars, chars_col, layout_type=None):
        assert isinstance(blocks, list)
        assert isinstance(columns, list)
        assert isinstance(chars, list)
        reorder = dict(blocks=True, columns=True, chars=True)
        if chars_col:
            assert isinstance(chars_col, list) and isinstance(chars_col[0], list) and isinstance(chars_col[0][0], int)

        if reorder.get('blocks'):
            blocks = CutTool.sort_blocks(blocks)
        if reorder.get('columns') and blocks:
            columns = CutTool.sort_columns(columns, blocks)

        if reorder.get('chars') and chars:
            return CutTool.sort(chars, columns, blocks, layout_type, chars_col)

    @staticmethod
    def gen_ocr_text(page, blocks=None, columns=None, chars=None):
        """根据当前字序生成页面的ocr和ocr_col文本，假定已按编号排序"""
        blocks = blocks or page['blocks']
        columns = columns or page['columns']
        chars = chars or page['chars']
        try:
            chars.sort(key=itemgetter('block_no', 'line_no', 'no'))
        except KeyError:
            pass

        # 根据列框的ocr_txt，生成页面的ocr_col，栏间用||分隔
        try:
            if not page.get('ocr_col'):
                page['ocr_col'] = '||'.join('|'.join(c['ocr_txt'] for c in columns if c['block_no'] == b['block_no'])
                                            for b in blocks)
        except KeyError:
            pass

        # 生成页面的ocr，按字序把每个字框的ocr_txt组合而成，栏间用||分隔
        texts = {'blocks': []}
        for c in chars:
            if c.get('ocr_txt') and c.get('line_no') and c.get('block_no'):
                block = texts.get(str(c['block_no']))
                if not block:
                    block = texts[str(c['block_no'])] = {'columns': []}
                    texts['blocks'].append(block)
                col = block.get(str(c['line_no']))
                if not col:
                    col = block[str(c['line_no'])] = {'txt': ''}
                    block['columns'].append(col)
                col['txt'] += c['ocr_txt']

        page['ocr'] = '||'.join('|'.join(c['txt'] for c in b['columns']) for b in texts['blocks'])
        for c in columns:
            c.pop('txt', None)

        return page
