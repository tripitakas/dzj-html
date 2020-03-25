#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from .tool.box import Box
from .tool.diff import Diff
from tornado.escape import url_escape
from controller.data.data import Page
from controller.task.base import TaskHandler


class PageHandler(TaskHandler, Page, Box):

    def __init__(self, application, request, **kwargs):
        super(PageHandler, self).__init__(application, request, **kwargs)
        self.chars_col = self.texts = self.doubts = []
        self.page_name = ''
        self.page = {}

    def prepare(self):
        super().prepare()
        self.page_name, self.page = self.doc_id, self.doc

    def page_title(self):
        return '%s-%s' % (self.task_name(), self.page.get('name') or '')

    def get_txt(self, key):
        if key == 'cmp':
            return self.page.get('cmp')
        if key == 'ocr':
            return self.page.get('ocr') or self.get_box_ocr(self.page.get('chars'))
        if key == 'ocr_col':
            return self.page.get('ocr_col') or self.get_box_ocr(self.page.get('columns'))
        if key == 'text':
            return self.page.get('text') or self.html2txt(self.page.get('txt_html', ''))

    def get_page_img(self, page=None, page_name=None):
        page_name = page_name if page_name else page.get('name')
        return self.get_web_img(page_name)

    @classmethod
    def get_box_ocr(cls, boxes):
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
    def char2html(cls, chars, field='txt'):
        if not chars:
            return ''
        pre, html = chars[0], '<div class="blocks"><div class="block"><div class="line">'
        for b in chars[1:]:
            if pre.get('block_no') and b.get('block_no') and pre['block_no'] != b['block_no']:
                html += '</div></div><div class="block"><div class="line">'
            elif pre.get('column_no') and b.get('column_no') and pre['column_no'] != b['column_no']:
                html += '</div><div class="line">'
            if b.get(field):
                html += '<span id="%s" class="char">%s</span>' % (b['cid'], b[field])
            pre = b
        return html + '</div></div></div>'

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

    def get_cmp_data(self):
        """ 获取比对文本、存疑文本"""
        texts, doubts = [], []
        if 'text_proof_' in self.task_type:
            doubts.append([self.prop(self.task, 'result.doubt', ''), '我的存疑'])
            for field in ['text', 'ocr', 'ocr_col', 'cmp']:
                if self.get_txt(field):
                    texts.append([self.get_txt(field), field, Page.get_field_name(field)])
        elif self.task_type == 'text_review':
            doubts.append([self.prop(self.task, 'result.doubt', ''), '我的存疑'])
            proof_doubt = ''
            condition = dict(task_type={'$regex': 'text_proof'}, doc_id=self.page_name, status=self.STATUS_FINISHED)
            for task in list(self.db.task.find(condition)):
                txt = self.html2txt(self.prop(task, 'result.txt_html', ''))
                texts.append([txt, task['task_type'], self.get_task_name(task['task_type'])])
                proof_doubt += self.prop(task, 'result.doubt', '')
            if proof_doubt:
                doubts.append([proof_doubt, '校对存疑'])
        elif self.task_type == 'text_hard':
            doubts.append([self.prop(self.task, 'result.doubt', ''), '难字列表'])
            condition = dict(task_type='text_review', doc_id=self.page['name'], status=self.STATUS_FINISHED)
            review_task = self.db.task.find_one(condition)
            review_doubt = self.prop(review_task, 'result.doubt', '')
            if review_doubt:
                doubts.append([review_doubt, '审定存疑'])
        return texts, doubts

    def get_txt_html_update(self, txt_html):
        """ 获取page的txt_html字段的更新"""
        text = self.html2txt(txt_html)
        is_match = self.check_match(self.page.get('chars'), text)[0]
        update = {'text': text, 'txt_html': txt_html, 'is_match': is_match}
        if is_match:
            update['chars'] = self.update_chars_txt(self.page.get('chars'), text)
        return update

    def get_box_update(self):
        """ 获取切分校对的提交"""
        # 过滤页面外的切分框
        blocks, columns, chars = self.filter_box(self.data, self.page['width'], self.page['height'])
        # 更新cid
        self.update_box_cid(chars)
        self.update_box_cid(columns)
        # 重新排序
        blocks = self.calc_block_id(blocks)
        columns = self.calc_column_id(columns, blocks)
        chars = self.calc_char_id(chars, columns, detect_col=self.data.get('detect_col', True))
        # 根据字框调整列框和栏框的边界
        if self.data.get('auto_adjust'):
            blocks = self.adjust_blocks(blocks, chars)
            columns = self.adjust_columns(columns, chars)
        # 合并用户字序和算法字序
        chars_col = []
        if self.page.get('chars_col'):
            algorithm_chars_col = self.get_chars_col(chars)
            chars_col = self.merge_chars_col(algorithm_chars_col, self.page['chars_col'])
            chars = self.update_char_order(chars, chars_col)
        # 设置更新字段
        ret = dict(chars=chars, blocks=blocks, columns=columns)
        if chars_col:
            ret['chars_col'] = chars_col
        return ret

    @staticmethod
    def get_all_txt(page):
        return [(page[f], f, Page.get_field_name(f)) for f in ['text', 'ocr', 'ocr_col', 'cmp'] if page.get(f)]

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
        # 1.生成segments
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
        # 2.结构化，以便页面输出
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
