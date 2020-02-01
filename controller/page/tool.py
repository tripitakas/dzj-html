#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 页
@time: 2019/6/3
"""
import re
from operator import itemgetter
from tornado.escape import url_escape


class PageTool(object):

    @classmethod
    def reorder_chars(cls, chars_col, chars, page=None):
        """ 根据连线数据排列字序"""
        return chars

    @classmethod
    def sort_boxes(cls, boxes, box_type, page=None):
        """ 切分框重新排序"""
        if box_type == 'block':
            return cls.sort_blocks(boxes)
        return boxes

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
        lines = []
        regex = re.compile("<li.*?>.*?</li>", re.M | re.S)
        for line in regex.findall(html or ''):
            if 'delete' not in line:
                txt = re.sub(r'(<li.*?>|</li>|<span.*?>|</span>|\s)', '', line, flags=re.M | re.S)
                lines.append(txt + '\n')
        return ''.join(lines).rstrip('\n')

    @classmethod
    def get_ocr(cls, page, chars=None):
        """ 获取页面的ocr文本"""
        ocr = page.get('ocr') or ''
        chars = chars if chars else page.get('chars')
        if not ocr and len(chars) > 1:
            pre, txt = chars[0], ''
            for c in chars[1:]:
                if pre.get('block_no') and c.get('block_no') and pre['block_no'] != c['block_no']:
                    txt += '||'
                elif pre.get('line_no') and c.get('line_no') and pre['line_no'] != c['line_no']:
                    txt += '|'
                txt += c.get('ocr_txt', '')
            ocr = txt.strip('|')
        return ocr

    @classmethod
    def get_ocr_col(cls, page, columns=None):
        """ 获取页面的ocr_col文本"""
        ocr_col = page.get('ocr_col') or ''
        columns = columns if columns else page.get('columns')
        if not ocr_col and len(columns) > 1:
            pre, txt = columns[0], ''
            for c in columns[1:]:
                if pre.get('block_no') and c.get('block_no') and pre['block_no'] != c['block_no']:
                    txt += '||'
                elif pre.get('line_no') and c.get('line_no') and pre['line_no'] != c['line_no']:
                    txt += '|'
                txt += c.get('ocr_txt', '')
            ocr_col = txt.strip('|')
        return ocr_col

    @classmethod
    def check_segments(cls, segments, chars, params=None):
        """ 检查segments """
        params = params or {}

        # 按列对字框分组，提取列号
        cls.normalize_boxes(dict(chars=chars, columns=params.get('columns') or []))
        column_ids = sorted(list(set((c['block_no'], c['line_no']) for c in chars)))

        # 然后逐行对应并分配栏列号，匹配时不做文字比较
        # 输入参数txt与字框的OCR文字通常是顺序一致的，假定文字的行分布与字框的列分布一致
        line_no = 0
        matched_boxes = []
        for seg in segments:
            if seg['line_no'] > len(column_ids):
                break
            if line_no != seg['line_no']:
                line_no = seg['line_no']
                boxes = [c for c in chars if (c['block_no'], c['line_no']) == column_ids[line_no - 1]]
                column_txt = ''.join(s.get('base', '') for s in segments if s['line_no'] == line_no)
                column_strip = re.sub(r'\s', '', column_txt)

                if len(boxes) != len(column_strip) and 'mismatch_lines' in params:
                    params['mismatch_lines'].append('b%dc%d' % (boxes[0]['block_no'], boxes[0]['line_no']))
                for i, c in enumerate(sorted(boxes, key=itemgetter('no'))):
                    c['txt'] = column_strip[i] if i < len(column_strip) else '?'
                    matched_boxes.append(c)

            seg['txt_line_no'] = seg.get('txt_line_no', seg['line_no'])
            seg['block_no'], seg['line_no'] = column_ids[line_no - 1]

            column_strip = re.sub(r'\s', '', seg.get('base', ''))
            char_codes = [(c, url_escape(c)) for c in list(column_strip)]
            seg['utf8mb4'] = ','.join([c for c, es in char_codes if len(es) > 9])

        for c in chars:
            if c not in matched_boxes:
                c.pop('txt', 0)

        return segments

    @staticmethod
    def normalize_boxes(page):
        for c in page.get('chars', []):
            cid = c.get('char_id', '')[1:].split('c')
            if len(cid) == 3:
                c['no'] = c['char_no'] = int(cid[2])
                c['block_no'], c['line_no'] = int(cid[0]), int(cid[1])
            else:
                c['no'] = c['char_no'] = c.get('char_no') or c.get('no', 0)
                c['block_no'] = c.get('block_no', 0)
                c['line_no'] = c.get('line_no', 0)
                c['char_id'] = 'b%dc%dc%d' % (c.get('block_no'), c.get('line_no'), c.get('no'))
        for c in page.get('columns', []):
            c.pop('char_id', 0)
            c.pop('char_no', 0)
