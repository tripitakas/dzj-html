#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import UIModule
from tornado.escape import to_basestring
from .base import PageHandler
from controller import errors as e


class TaskCutHandler(PageHandler):
    URL = ['/task/@cut_task/@task_id',
           '/task/do/@cut_task/@task_id',
           '/task/browse/@cut_task/@task_id',
           '/task/update/@cut_task/@task_id']

    config_fields = [
        dict(id='auto-pick', name='提交后自动领新任务', input_type='radio', options=['是', '否'], default='是'),
        dict(id='auto-adjust', name='自适应调整栏框和列框', input_type='radio', options=['是', '否'], default='是'),
        dict(id='detect-col', name='自适应调整字框在多列的情况', input_type='radio', options=['是', '否'], default='是'),
    ]

    def get(self, task_type, task_id):
        """ 切分校对页面"""
        try:
            template = 'page_task_cut.html'
            if self.steps['current'] == 'order':
                template = 'task_cut_order.html'
                reorder = self.get_query_argument('reorder', '')
                if reorder:
                    boxes = self.reorder_boxes(page=self.page, direction=reorder)
                    self.page['blocks'], self.page['columns'], self.page['chars'] = boxes
                self.chars_col = self.get_chars_col(self.page['chars'])
            self.render(template)

        except Exception as error:
            return self.send_db_error(error)


class CutEditHandler(PageHandler):
    URL = ['/page/cut_edit/@page_name',
           '/page/cut_view/@page_name']

    config_fields = [
        dict(id='auto-adjust', name='自适应调整栏框和列框', input_type='radio', options=['是', '否'], default='是'),
        dict(id='detect-col', name='自动调整字框在多列的情况', input_type='radio', options=['是', '否'], default='是'),
    ]

    def get(self, page_name):
        """ 切分编辑页面"""
        try:
            template = 'page_task_cut.html'
            if self.steps['current'] == 'order':
                template = 'page_task_order.html'
                reorder = self.get_query_argument('reorder', '')
                if reorder:
                    boxes = self.reorder_boxes(page=self.page, direction=reorder)
                    self.page['blocks'], self.page['columns'], self.page['chars'] = boxes
                self.chars_col = self.get_chars_col(self.page['chars'])
            self.render(template)

        except Exception as error:
            return self.send_db_error(error)


class TaskTextProofHandler(PageHandler):
    URL = ['/task/text_proof_@num/@task_id',
           '/task/do/text_proof_@num/@task_id',
           '/task/browse/text_proof_@num/@task_id',
           '/task/update/text_proof_@num/@task_id']

    def get(self, num, task_id):
        """ 文字校对页面"""
        try:
            self.texts, self.doubts = self.get_cmp_txt()
            if self.steps['current'] == 'select':
                cmp = self.prop(self.task, 'result.cmp')
                return self.render('page_task_select.html', cmp=cmp)
            else:
                cmp_data = self.prop(self.task, 'result.txt_html')
                if not cmp_data or self.get_query_argument('re_compare', '') == 'true':
                    cmp_data = self.diff(*[t[0] for t in self.texts])
                    cmp_data = to_basestring(TextArea(self).render(cmp_data))
                return self.render('page_task_text.html', cmp_data=cmp_data)

        except Exception as error:
            return self.send_db_error(error)


class TaskTextReviewHandler(PageHandler):
    URL = ['/task/(text_review|text_hard)/@task_id',
           '/task/do/(text_review|text_hard)/@task_id',
           '/task/browse/(text_review|text_hard)/@task_id',
           '/task/update/(text_review|text_hard)/@task_id']

    def get(self, task_type, task_id):
        """ 文字审定、难字审定页面"""
        try:
            self.texts, self.doubts = self.get_cmp_txt()
            cmp_data = self.prop(self.page, 'txt_html')
            if not cmp_data and len(self.texts):
                cmp_data = self.diff(*[t[0] for t in self.texts])
            self.render('page_task_text.html', cmp_data=cmp_data)

        except Exception as error:
            return self.send_db_error(error)


class TextEditHandler(PageHandler):
    URL = ['/page/text_edit/@page_name',
           '/page/text_view/@page_name']

    def get(self, page_name):
        """ 文字查看、修改页面"""
        try:
            self.texts, self.doubts = self.get_cmp_txt()
            cmp_data, text = self.page.get('txt_html') or '', self.page.get('text') or ''
            if not cmp_data and not text:
                self.send_error_response(e.no_object, message='没有找到审定文本')

            if not cmp_data and text:
                cmp_data = self.diff(text)
                cmp_data = to_basestring(TextArea(self).render(cmp_data))

            self.render('page_task_text.html', cmp_data=cmp_data)

        except Exception as error:
            return self.send_db_error(error)


class TextArea(UIModule):
    """文字校对的文字区"""

    def render(self, cmp_data):
        return self.render_string('page_text_area.html', blocks=cmp_data)
