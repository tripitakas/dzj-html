#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经OCR
@time: 2019/9/2
"""
from operator import itemgetter
from controller.cut.v2 import calc


def ocr2page(page):
    def union(r1, r2):
        if not r1:
            r1 = list(r2)
        else:
            r1[0] = min(r1[0], r2[0])  # x1
            r1[1] = min(r1[1], r2[1])  # y1
            r1[2] = max(r1[2], r2[2])  # x2
            r1[3] = max(r1[3], r2[3])  # y2
        return r1

    def union_list(items):
        ret = None
        for r in items:
            ret = union(ret, r)
        return dict(x=ret[0], y=ret[1], w=ret[2] - ret[0], h=ret[3] - ret[1])

    page['blocks'], page['columns'] = [], []
    if 'chars_pos' in page:
        block = union_list(page['chars_pos'])
        block.update(dict(block_id='b1', no=1))
        page['blocks'] = [block]
        page['chars'] = [
            dict(x=c[0], y=c[1], w=c[2] - c[0], h=c[3] - c[1], cc=page['chars_cc'][i], txt=page['chars_text'][i])
            for i, c in enumerate(page['chars_pos'])
        ]
    chars = calc(page['chars'], page['blocks'], [])
    for c_i, c in enumerate(chars):
        page['chars'][c_i]['char_id'] = 'b%dc%dc%d' % (c['block_id'], c['column_id'], c['column_order'])
        page['chars'][c_i]['block_no'] = c['block_id']
        page['chars'][c_i]['line_no'] = c['column_id']
        page['chars'][c_i]['char_no'] = page['chars'][c_i]['no'] = chars[c_i]['no'] = c['column_order']
    page['chars'].sort(key=itemgetter('block_no', 'line_no', 'char_no'))
    columns, max_h = {}, 0
    for c_i, c in enumerate(page['chars']):
        column_id = 'b%dc%d' % (c['block_no'], c['line_no'])
        if column_id not in columns:
            columns[column_id] = dict(column_id=column_id, block_no=c['block_no'], line_no=c['line_no'],
                                      txt='', no=c['line_no'])
            chars_col = [
                [s['x'], s['y'], s['x'] + s['w'], s['y'] + s['h']]
                for i, s in enumerate(page['chars'])
                if chars[i]['block_id'] == c['block_no'] and chars[i]['column_id'] == c['line_no']
            ]
            columns[column_id].update(union_list(chars_col))
            page['columns'].append(columns[column_id])
            max_h = c['h']
        max_h = max(max_h, c['h'])
        if columns[column_id]['txt']:
            last = page['chars'][c_i - 1]
            if c['y'] - (last['y'] + last['h']) > max_h / 2:
                columns[column_id]['txt'] += '　'
        columns[column_id]['txt'] += c['txt']
    page['ocr'] = [c['txt'] for c in page["columns"]]
    if page.get('lines_text'):
        page['ocr'] = page['lines_text']
    return page
