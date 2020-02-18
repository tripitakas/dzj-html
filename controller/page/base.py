#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

    def get_box_updated(self):
        """ 获取切分校对的提交"""
        # 过滤页面外的切分框
        blocks, columns, chars = self.filter_box(self.data, self.page['width'], self.page['height'])
        # 更新cid
        self.update_chars_cid(chars)
        # 重新排序
        blocks = self.calc_block_id(blocks)
        columns = self.calc_column_id(columns, blocks)
        chars = self.calc_char_id(chars, columns, detect_col=self.data.get('detect_col') or True)
        # 根据字框调整列框和栏框的大小
        if self.data.get('auto_adjust'):
            self.adjust_blocks(blocks, chars)
            self.adjust_columns(columns, chars)
        # 合并用户校对的字序和算法字序
        if self.page.get('chars_col'):
            chars = self.update_char_order(chars, self.page.get('chars_col'))

        return dict(chars=chars, blocks=blocks, columns=columns)

    def reorder(self):
        """ 重排序号"""
        self.page['blocks'], self.page['columns'], self.page['chars'] = self.reorder_boxes(page=self.page)
