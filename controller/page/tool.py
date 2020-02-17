#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 页面工具
@time: 2019/6/3
"""
import re
from operator import itemgetter
from controller.page.diff import Diff
from tornado.escape import url_escape
from controller.page.box import BoxTool


class PageTool(BoxTool):

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
    def reorder_boxes(cls, chars=None, columns=None, blocks=None, page=None):
        if not chars and page:
            blocks = page.get('blocks') or []
            columns = page.get('columns') or []
            chars = page.get('chars') or []
        blocks = cls.calc_block_id(blocks)
        columns = cls.calc_column_id(columns, blocks)
        chars = cls.calc_char_id(chars, columns)
        return blocks, columns, chars

    @classmethod
    def get_chars_col(cls, chars):
        """ 按照column_no对chars分组并设置cid。假定chars已排序"""
        ret = []
        cid_col = [chars[0]['cid']]
        for i, c in enumerate(chars[1:]):
            cur_no = c.get('column_no')
            pre_no = chars[i].get('column_no')
            if cur_no is not None and pre_no is not None and cur_no != pre_no:  # 换行
                ret.append(cid_col)
                cid_col = [c['cid']]
            else:
                cid_col.append(c['cid'])
        if cid_col:
            ret.append(cid_col)
        return ret

    @classmethod
    def update_char_order(cls, chars, chars_col):
        """ 按照chars_col重排chars"""
        block_no = column_no = 0
        for col_order in chars_col:
            column_no += 1
            for char_no, cid in enumerate(col_order):
                cs = [c for c in chars if c['cid'] == cid]
                if cs:
                    c = cs[0]
                    if block_no != c['block_no']:
                        block_no = c['block_no']
                        column_no = 1
                    c['column_no'] = column_no
                    c['char_no'] = char_no + 1
                    c['char_id'] = 'b%sc%sc%s' % (c['block_no'], c['column_no'], c['char_no'])
        return sorted(chars, key=itemgetter('block_no', 'column_no', 'char_no'))

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
                    line_txt = re.sub(r'(<li.*?>|</li>|<span.*?>|</span>|<[^>]+>|\s)', '', line, flags=re.M | re.S)
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
            if not (s['is_same'] and s['base'] == '\n'):
                s['offset'] = s['range'][0]
                blocks[b_no][l_no].append(s)
        return blocks
