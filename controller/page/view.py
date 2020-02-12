#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
from tornado.web import UIModule
from controller import errors as e
from controller.page.base import PageHandler


class CutTaskHandler(PageHandler):
    URL = ['/task/@cut_task/@task_id',
           '/task/do/@cut_task/@task_id',
           '/task/browse/@cut_task/@task_id',
           '/task/update/@cut_task/@task_id']

    def get(self, task_type, task_id):
        """ 切分校对页面"""
        try:
            btn_config = {}
            template = 'task_cut_do.html'
            if self.steps['current'] == 'order':
                template = 'task_cut_order.html'
                if self.get_query_argument('reorder', '') == 'true':
                    self.reorder()
                self.chars_col = self.get_chars_col(self.page['chars'])
            self.render(template, btn_config=btn_config)

        except Exception as error:
            return self.send_db_error(error)


class CutEditHandler(PageHandler):
    URL = ['/data/cut_edit/@page_name',
           '/data/cut_view/@page_name']

    def get(self, page_name):
        """ 切分编辑页面"""
        try:
            btn_config = {}
            template = 'task_cut_do.html'
            if self.steps['current'] == 'order':
                template = 'task_cut_order.html'
                if self.get_query_argument('reorder', '') == 'true':
                    self.reorder()
                self.chars_col = self.get_chars_col(self.page['chars'])
            self.render(template, btn_config=btn_config)

        except Exception as error:
            return self.send_db_error(error)


class TextProofHandler(PageHandler):
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
                return self.render('task_text_select.html', cmp=cmp)
            else:
                cmp_data = self.prop(self.task, 'result.txt_html')
                if not cmp_data or self.get_query_argument('re_compare', '') == 'true':
                    cmp_data = self.diff(*[t[0] for t in self.texts])
                return self.render('task_text_do.html', cmp_data=cmp_data)

        except Exception as error:
            return self.send_db_error(error)


class TextReviewHandler(PageHandler):
    URL = ['/task/(text_review|text_hard)/@task_id',
           '/task/do/(text_review|text_hard)/@task_id',
           '/task/browse/(text_review|text_hard)/@task_id',
           '/task/update/(text_review|text_hard)/@task_id']

    def get(self, task_type, task_id):
        """ 文字审定、难字审定页面"""
        try:
            self.texts, self.doubts = self.get_cmp_txt()
            cmp_data = self.prop(self.page, 'txt_html')
            if not cmp_data:
                cmp_data = self.diff(*[t[0] for t in self.texts])
            self.render('task_text_do.html', cmp_data=cmp_data)

        except Exception as error:
            return self.send_db_error(error)


class TextEditHandler(PageHandler):
    URL = '/data/text_edit/@page_name'

    def get(self, page_name):
        """ 文字修改页面"""
        try:
            self.texts, self.doubts = self.get_cmp_txt()
            cmp_data, text = self.page.get('txt_html') or '', self.page.get('text') or ''
            if not cmp_data and not text:
                self.send_error_response(e.no_object, message='没有找到审定文本')

            if not cmp_data and text:
                cmp_data = self.diff(text)
            self.render('task_text_do.html', cmp_data=cmp_data)

        except Exception as error:
            return self.send_db_error(error)


class TextArea(UIModule):
    """文字校对的文字区"""

    def render(self, cmp_data):
        return self.render_string('_text_area.html', blocks=cmp_data)
