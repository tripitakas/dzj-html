#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from datetime import datetime
from bson.objectid import ObjectId
from controller.page.tool import PageTool
from controller.task.base import TaskHandler


class PageHandler(TaskHandler, PageTool):
    step2box = dict(chars='char', columns='column', blocks='block', orders='char')

    def __init__(self, application, request, **kwargs):
        super(TaskHandler, self).__init__(application, request, **kwargs)
        self.boxes = self.texts = self.doubts = []
        self.box_type = self.page_name = ''
        self.page = {}

    def prepare(self):
        super().prepare()
        if self.error:
            return
        self.page_name, self.page = self.doc_id, self.doc
        if not self.is_api:
            # 设置切分任务参数
            if self.task_type in ['cut_proof', 'cut_review']:
                self.box_type = self.step2box.get(self.steps['current'])
                self.boxes = self.page.get(self.box_type + 's')
            # 设置文字任务参数
            if 'text_' in self.task_type:
                self.texts, self.doubts = self.get_cmp_txt()

    def get_task_type(self):
        """ 重载父类函数"""
        task_type = super().get_task_type()
        if not task_type:
            # edit模式时，设置task_type
            p = self.request.path
            return 'cut_proof' if '/edit/box' in p else 'text_proof_1' if '/edit/text' in p else ''

    def get_doc_id(self):
        """ 重载父类函数"""
        regex = r'/([a-zA-Z]{2}(_\d+)+)(\?|$|\/)'
        s = re.search(regex, self.request.path)
        return s.group(1) if s else ''

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

    def submit_task(self, data):
        """ 提交任务"""
        update = {'updated_time': datetime.now(), 'steps.submitted': self.get_submitted(data['step'])}
        self.db.task.update_one({'_id': ObjectId(self.task_id)}, {'$set': update})
        steps_todo = self.prop(self.task, 'steps.todo', [])
        if data['step'] == steps_todo[-1]:
            if self.mode == 'do':
                self.finish_task(self.task)
            else:
                self.release_temp_lock(self.task['doc_id'], 'box', self.current_user)

    def get_submitted(self, step):
        """ 更新task.steps.submitted字段"""
        submitted = self.prop(self.task, 'steps.submitted', [])
        if step not in submitted:
            submitted.append(step)
        return submitted

    def update_page_txt_html(self, txt_html):
        """ 更新page的txt_html字段"""
        text = self.html2txt(txt_html)
        is_match = self.check_match(self.page.get('chars'), text)
        update = {'text': text, 'txt_html': txt_html, 'is_match': is_match}
        if is_match:
            update['chars'] = self.update_chars_txt(self.page.get('chars'), text)
        self.db.page.update_one({'name': self.page_name}, {'$set': update})
