#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
from bson import json_util
from tornado.web import UIModule
from controller import errors as e
from controller.page.diff import Diff
from controller.page.base import PageHandler
from controller.cut.cuttool import CutTool


class CutTaskHandler(PageHandler):
    URL = ['/task/@cut_task/@task_id',
           '/task/do/@cut_task/@task_id',
           '/task/browse/@cut_task/@task_id',
           '/task/update/@cut_task/@task_id']

    def get(self, task_type, task_id):
        """ 切分校对页面"""
        try:
            template = 'task_cut_do.html'
            kwargs = dict()
            if self.steps['current'] == 'orders':
                kwargs = CutTool.char_render(self.page, int(self.get_query_argument('layout', 0)))
                kwargs['btn_config'] = json_util.loads(self.get_secure_cookie('%s_orders' % task_type) or '{}')
                template = 'task_cut_order.html'
            self.render(template, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class CutEditHandler(PageHandler):
    URL = '/task/cut_edit/@page_name'

    def get(self, page_name):
        """ 切分编辑页面"""
        try:
            template = 'task_cut_do.html'
            kwargs = dict()
            if self.steps['current'] == 'orders':
                kwargs = CutTool.char_render(self.page, int(self.get_query_argument('layout', 0)))
                template = 'task_cut_order.html'
            self.render(template, **kwargs)

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
            if self.steps['current'] == 'select':
                cmp = self.prop(self.task, 'result.cmp')
                return self.render('task_text_select.html', cmp=cmp)
            else:
                cmp_data = self.prop(self.task, 'result.txt_html')
                if not cmp_data or self.get_query_argument('re_compare', '') == 'true':
                    cmp_data = Diff.diff(*[t[0] for t in self.texts])[0]
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
            cmp_data = self.prop(self.page, 'txt_html')
            if not cmp_data:
                cmp_data = Diff.diff(*[t[0] for t in self.texts])[0]
            self.render('task_text_do.html', cmp_data=cmp_data)

        except Exception as error:
            return self.send_db_error(error)


class TextEditHandler(PageHandler):
    URL = '/task/text_edit/@page_name'

    def get(self, page_name):
        """ 文字修改页面"""
        try:
            cmp_data, text = self.page.get('txt_html') or '', self.page.get('text') or ''
            if not cmp_data and not text:
                self.send_error_response(e.no_object, message='没有找到审定文本')

            if not cmp_data and text:
                cmp_data = Diff.diff(text)[0]
            self.render('task_text_do.html', cmp_data=cmp_data)

        except Exception as error:
            return self.send_db_error(error)


class TextArea(UIModule):
    """文字校对的文字区"""

    def render(self, segments, raw=False):
        cur_line_no, items, lines = 0, [], []
        blocks = [dict(block_no=1, lines=lines)]
        for item in segments:
            if 'block_no' in item and item['block_no'] != blocks[-1]['block_no']:
                lines = []
                blocks.append(dict(block_no=blocks[-1]['block_no'] + 1, lines=lines))
            if item['line_no'] != cur_line_no:
                cur_line_no = item['line_no']
                items = [item]
                lines.append(dict(line_no=cur_line_no, items=items))
                item['offset'] = 0
            elif items:
                item['offset'] = items[-1]['offset'] + len(items[-1]['base'])
                if item['base'] != '\n':
                    items.append(item)
            item['block_no'] = blocks[-1]['block_no']

        return dict(blocks=blocks) if raw else self.render_string('_text_area.html', blocks=blocks)
