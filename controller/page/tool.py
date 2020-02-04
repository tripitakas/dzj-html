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
        return None

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
        """ 从html中获取txt文本，换行用|、换栏用||表示"""
        txt = ''
        regex1 = re.compile("<ul.*?>.*?</ul>", re.M | re.S)
        regex2 = re.compile("<li.*?>.*?</li>", re.M | re.S)
        for block in regex1.findall(html or ''):
            for line in regex2.findall(block or ''):
                if 'delete' not in line:
                    line_txt = re.sub(r'(<li.*?>|</li>|<span.*?>|</span>|\s)', '', line, flags=re.M | re.S)
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
        return txt.strip('|')

    @classmethod
    def gen_segments(cls, texts):
        """ 根据texts列表，生成文字校对的segment"""
        pass

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

    @staticmethod
    def check_match(chars, txt):
        """ 检查图文是否匹配，包括总行数和每行字数"""
        char_line_num = []
        if chars:
            pre, num = chars[0], 1
            for c in chars[1:]:
                if pre.get('block_no') and c.get('block_no') and pre['block_no'] != c['block_no']:  # 换栏
                    char_line_num.append(num)
                    num = 1
                elif pre.get('line_no') and c.get('line_no') and pre['line_no'] != c['line_no']:  # 换行
                    char_line_num.append(num)
                    num = 1
                else:
                    num += 1
            char_line_num.append(num)

        txt_lines = re.sub(r'[\|\n]+', '|', txt).split('|')
        txt_line_num = [len(line) for line in txt_lines]

        mis_match = []
        if len(char_line_num) < len(txt_line_num):
            for i, num in enumerate(char_line_num):
                if num != txt_line_num[i]:
                    mis_match.append([i, num, txt_line_num[i]])
            for i in range(len(char_line_num), len(txt_line_num)):
                mis_match.append([i, 0, txt_line_num[i]])
        else:
            for i, num in enumerate(txt_line_num):
                if num != char_line_num[i]:
                    mis_match.append([i, char_line_num[i], num])
            for i in range(len(txt_line_num), len(char_line_num)):
                mis_match.append([i, char_line_num[i], 0])

        r = len(char_line_num) == len(txt_line_num) and not mis_match

        return r, mis_match, char_line_num, txt_line_num

    @staticmethod
    def update_chars_txt(chars, txt):
        """ 将txt回写到chars中。假定图文匹配"""
        txt = re.sub(r'[\|\n]+', '', txt)
        if len(chars) != len(txt):
            return False
        for i, c in enumerate(chars):
            c['txt'] = txt[i]
        return chars
