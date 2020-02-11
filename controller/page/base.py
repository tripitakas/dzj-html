#!/usr/bin/env python
# -*- coding: utf-8 -*-
from controller.page.diff import Diff
from tornado.escape import json_decode
from controller.page.tool import PageTool
from controller.task.base import TaskHandler


class PageHandler(TaskHandler, PageTool):
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

    def get_ocr(self):
        return self.page.get('ocr') or self.get_ocr_txt(self.page.get('chars'))

    def get_ocr_col(self):
        return self.page.get('ocr_col') or self.get_ocr_txt(self.page.get('columns'))

    def get_cmp_txt(self):
        """ 获取比对文本、存疑文本"""
        texts, doubts = [], []
        if 'text_proof_' in self.task_type:
            doubt = self.prop(self.task, 'result.doubt', '')
            doubts.append([doubt, '我的存疑'])
            ocr = self.get_ocr()
            if ocr:
                texts.append([ocr, '字框OCR'])
            ocr_col = self.get_ocr_col()
            if ocr_col:
                texts.append([ocr_col, '列框OCR'])
            cmp = self.prop(self.task, 'result.cmp')
            if cmp:
                texts.append([cmp, '比对文本'])
        elif self.task_type == 'text_review':
            doubt = self.prop(self.task, 'result.doubt', '')
            doubts.append([doubt, '我的存疑'])
            proof_doubt = ''
            condition = dict(task_type={'$regex': 'text_proof'}, doc_id=self.page_name, status=self.STATUS_FINISHED)
            for task in list(self.db.task.find(condition)):
                txt = self.html2txt(self.prop(task, 'result.txt_html', ''))
                texts.append([txt, self.get_task_name(task['task_type'])])
                proof_doubt += self.prop(task, 'result.doubt', '')
            if proof_doubt:
                doubts.append([proof_doubt, '校对存疑'])
        elif self.task_type == 'text_hard':
            doubt = self.prop(self.task, 'result.doubt', '')
            doubts.append([doubt, '难字列表'])
            condition = dict(task_type='text_review', doc_id=self.page['name'], status=self.STATUS_FINISHED)
            review_task = self.db.task.find_one(condition)
            review_doubt = self.prop(review_task, 'result.doubt', '')
            if review_doubt:
                doubts.append([review_doubt, '审定存疑'])
        return texts, doubts

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

    def get_txt_html_update(self, txt_html):
        """ 获取page的txt_html字段的更新"""
        text = self.html2txt(txt_html)
        is_match = self.check_match(self.page.get('chars'), text)[0]
        update = {'text': text, 'txt_html': txt_html, 'is_match': is_match}
        if is_match:
            update['chars'] = self.update_chars_txt(self.page.get('chars'), text)
        return update

    @staticmethod
    def decode_box(boxes):
        return json_decode(boxes) if isinstance(boxes, str) else boxes

    def check_box_cover(self, auto_filter=False):
        """ 检查字框覆盖情况。auto_filter为True时，过滤字框并设置好self.data"""
        chars = self.decode_box(self.data['chars'])
        blocks = self.decode_box(self.data['blocks'])
        columns = self.decode_box(self.data['columns'])
        char_out_block, char_in_block = self.boxes_out_boxes(chars, blocks)
        if char_out_block:
            if auto_filter:
                self.data['chars'] = char_in_block
            return False, '字框不在栏框内', [c['char_id'] for c in char_out_block]
        column_out_block, column_in_block = self.boxes_out_boxes(columns, blocks)
        if column_out_block:
            if auto_filter:
                self.data['columns'] = column_in_block
            return False, '列框不在栏框内', [c['column_id'] for c in column_out_block]
        char_out_column, char_in_column = self.boxes_out_boxes(chars, columns)
        if char_out_column:
            if auto_filter:
                self.data['chars'] = char_in_column
            return False, '字框不在列框内', [c['char_id'] for c in char_out_column]
        return True, None, []

    @staticmethod
    def update_chars_cid(chars):
        max_cid = max([int(c.get('cid') or 0) for c in chars])
        for c in chars:
            if not c.get('cid'):
                c['cid'] = max_cid + 1
                max_cid += 1

    def get_box_updated(self, calc_id=None):
        """ 获取切分校对的提交"""
        chars = self.decode_box(self.data['chars'])
        self.update_chars_cid(chars)
        blocks = self.decode_box(self.data['blocks'])
        columns = self.decode_box(self.data['columns'])
        if calc_id:
            blocks = self.calc_block_id(blocks)
            columns = self.calc_column_id(columns, blocks)
            chars = self.calc_char_id(chars, columns)
        return dict(chars=chars, blocks=blocks, columns=columns)

    def reorder(self):
        """ 重排序号"""
        self.page['blocks'], self.page['columns'], self.page['chars'] = self.re_calc_id(page=self.page)
