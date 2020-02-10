#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

    def check_box_cover(self):
        chars = self.decode_box(self.data['chars'])
        blocks = self.decode_box(self.data['blocks'])
        columns = self.decode_box(self.data['columns'])
        char_not_in_block = self.boxes_not_in_boxes(chars, blocks)
        if not char_not_in_block:
            return False, '检测到有字框不在栏框内', [c['char_id'] for c in char_not_in_block]
        column_not_in_block = self.boxes_not_in_boxes(columns, blocks)
        if not column_not_in_block:
            return False, '检测到有列框不在栏框内', [c['column_id'] for c in column_not_in_block]
        char_not_in_column = self.boxes_not_in_boxes(chars, columns)
        if not char_not_in_column:
            return False, '检测到有字框不在列框内', [c['char_id'] for c in char_not_in_column]
        return True, None, []

    def get_cut_submit(self, calc_id=None, auto_filter=False):
        """ 获取切分校对的提交
        :param calc_id: 是否重新计算id
        :param auto_filter: 是否自动过滤掉栏外的列框和字框。只有calc_id为True时，参数才有效
        """
        if calc_id is None and not self.page.get('order_confirmed'):
            calc_id = True
        chars = self.decode_box(self.data['chars'])
        blocks = self.decode_box(self.data['blocks'])
        columns = self.decode_box(self.data['columns'])
        if calc_id:
            blocks = self.calc_block_id(blocks)
            columns = self.calc_column_id(columns, blocks, auto_filter)
            chars = self.calc_char_id(chars, columns, auto_filter)
        return dict(chars=chars, blocks=blocks, columns=columns)

    def reorder(self):
        """ 重排序号"""
        self.page['blocks'], self.page['columns'], self.page['chars'] = self.re_calc_id(page=self.page)
