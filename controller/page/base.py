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
            if 'cut_' in self.task_type:
                self.box_type = self.step2box.get(self.steps['current'])
                self.boxes = self.page.get(self.box_type + 's')
            # 设置文字任务参数
            if 'text_' in self.task_type:
                self.texts, self.doubts = self.get_cmp_txt()

    def get_task_type(self):
        """ 重载父类函数"""
        task_type = super().get_task_type()
        if not task_type:  # task_type缺省设置(如edit模式或sample示例时)
            p = self.request.path
            return 'cut_proof' if '/box' in p else 'text_proof_1' if '/text' in p else ''

    def get_doc_id(self):
        """ 重载父类函数"""
        regex = r'/([a-zA-Z]{2}(_\d+)+)(\?|$|\/)'
        s = re.search(regex, self.request.path)
        return s.group(1) if s else ''

    def page_title(self):
        return '%s-%s' % (self.task_name(), self.page.get('name') or '')

    def get_cmp_txt(self):
        """ 获取比对文本、存疑文本"""
        texts, doubts = [], []
        if 'text_proof' in self.task_type:
            doubt = self.prop(self.task, 'result.doubt', '')
            doubts.append([doubt, '我的存疑'])
            ocr = self.get_ocr(self.page)
            if ocr:
                texts.append([ocr, '字框OCR'])
            ocr_col = self.get_ocr_col(self.page)
            if ocr_col:
                texts.append([ocr_col, '列框OCR'])
            cmp = self.prop(self.task, 'result.cmp')
            if cmp:
                texts.append([cmp, '比对文本'])
        elif self.task_type == 'text_review':
            doubt = self.prop(self.task, 'result.doubt', '')
            doubts.append([doubt, '我的存疑'])
            proof_doubt = ''
            condition = dict(task_type={'$regex': 'text_proof'}, doc_id=self.page['name'], status=self.STATUS_FINISHED)
            for task in list(self.db.task.find(condition)):
                txt = self.html2txt(self.prop(task, 'result.txt_html', ''))
                texts.append([txt, self.get_task_name(task['task_type'])])
                doubt += self.prop(task, 'result.doubt', '')
            if proof_doubt:
                doubts.append([proof_doubt, '校对存疑'])
        elif self.task_type == 'text_hard':
            doubt = self.prop(self.task, 'result.doubt', '')
            doubts.append([doubt, '难字列表'])
            condition = dict(task_type='text_review', doc_id=self.page['name'], status=self.STATUS_FINISHED)
            task = self.db.task.find_one(condition)
            txt = self.html2txt(self.prop(task, 'result.txt_html', ''))
            texts.append([txt, self.get_task_name(task['task_type'])])
            review_doubt = self.prop(task, 'result.doubt', '')
            if review_doubt:
                doubts.append([review_doubt, '审定存疑'])
        return texts, doubts

    def submit_task(self, data):
        """ 提交任务"""
        submitted = self.prop(self.task, 'steps.submitted', [])
        if data['step'] not in submitted:
            submitted.append(data['step'])
        update = {'updated_time': datetime.now(), 'steps.submitted': submitted}
        self.db.task.update_one({'_id': ObjectId(self.task_id)}, {'$set': update})
        self.add_op_log('submit_%s' % self.task_type, target_id=self.task_id)
        steps_todo = self.prop(self.task, 'steps.todo', [])
        if data['step'] == steps_todo[-1]:
            if self.mode == 'do':
                self.finish_task(self.task)
            else:
                self.release_temp_lock(self.task['doc_id'], 'box', self.current_user)
