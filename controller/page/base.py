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
        """ 检查字框覆盖情况"""
        chars = self.decode_box(self.data['chars'])
        blocks = self.decode_box(self.data['blocks'])
        columns = self.decode_box(self.data['columns'])
        char_out_block, char_in_block = self.boxes_out_boxes(chars, blocks)
        if char_out_block:
            return False, '字框不在栏框内', [c['char_id'] for c in char_out_block]
        column_out_block, column_in_block = self.boxes_out_boxes(columns, blocks)
        if column_out_block:
            return False, '列框不在栏框内', [c['char_id'] for c in column_out_block]
        char_out_column, char_in_column = self.boxes_out_boxes(chars, columns)
        if char_out_column:
            return False, '字框不在列框内', [c['char_id'] for c in char_out_column]
        return True, None, []

    @staticmethod
    def update_chars_cid(chars):
        updated = False
        max_cid = max([int(c.get('cid') or 0) for c in chars])
        for c in chars:
            if not c.get('cid'):
                c['cid'] = max_cid + 1
                max_cid += 1
                updated = True
        return updated

    def get_box_updated(self, chars_cal=None):
        """ 获取切分校对的提交"""
        chars = self.decode_box(self.data['chars'])
        blocks = self.decode_box(self.data['blocks'])
        columns = self.decode_box(self.data['columns'])
        # 更新cid
        updated = self.update_chars_cid(chars)
        # 检查是否有新框
        new_chars = [c for c in chars if 'new' in c['char_id']]
        # 重新计算block_no/block_id/column_no/column_id/char_no/char_id
        blocks = self.calc_block_id(blocks)
        columns = self.calc_column_id(columns, blocks)
        chars = self.calc_char_id(chars, columns)
        # 如果没有新的cid也没有新框，则按用户的字序重新排序
        if not updated and not new_chars and chars_cal:
            chars = self.update_char_order(chars, chars_cal)

        return dict(chars=chars, blocks=blocks, columns=columns)

    def reorder(self):
        """ 重排序号"""
        self.page['blocks'], self.page['columns'], self.page['chars'] = self.re_calc_id(page=self.page)
