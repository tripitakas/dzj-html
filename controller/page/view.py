#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bson import json_util
from tornado.web import UIModule
from tornado.escape import to_basestring
from .base import PageHandler
from controller import errors as e


class TaskCutHandler(PageHandler):
    URL = ['/task/@cut_task/@task_id',
           '/task/do/@cut_task/@task_id',
           '/task/browse/@cut_task/@task_id',
           '/task/update/@cut_task/@task_id']

    def get(self, task_type, task_id):
        """ 切分校对页面"""
        kwargs = dict(input_type='radio', options=['是', '否'], default='是')
        config_fields = [
            dict(id='auto-pick', name='提交后自动领新任务', **kwargs),
            dict(id='auto-adjust', name='自适应调整栏框和列框', **kwargs),
            dict(id='detect-col', name='自适应调整字框在多列的情况', **kwargs),
        ]

        try:
            template = 'page_task_cut.html'
            if self.steps['current'] == 'order':
                template = 'page_task_order.html'
                reorder = self.get_query_argument('reorder', '')
                if reorder:
                    boxes = self.reorder_boxes(page=self.page, direction=reorder)
                    self.page['blocks'], self.page['columns'], self.page['chars'] = boxes
                self.chars_col = self.get_chars_col(self.page['chars'])
            self.render(template, page=self.page, img_url=self.get_page_img(self.page),
                        config_fields=config_fields, chars_col=self.chars_col)

        except Exception as error:
            return self.send_db_error(error)


class CutEditHandler(PageHandler):
    URL = ['/page/cut_edit/@page_name',
           '/page/cut_view/@page_name']

    def get(self, page_name):
        """ 切分编辑页面"""
        kwargs = dict(input_type='radio', options=['是', '否'], default='是')
        config_fields = [
            dict(id='auto-adjust', name='自适应调整栏框和列框', **kwargs),
            dict(id='detect-col', name='自适应调整字框在多列的情况', **kwargs),
        ]

        try:
            template = 'page_task_cut.html'
            if self.steps['current'] == 'order':
                template = 'page_task_order.html'
                reorder = self.get_query_argument('reorder', '')
                if reorder:
                    boxes = self.reorder_boxes(page=self.page, direction=reorder)
                    self.page['blocks'], self.page['columns'], self.page['chars'] = boxes
                self.chars_col = self.get_chars_col(self.page['chars'])
            self.render(template, page=self.page, img_url=self.get_page_img(self.page),
                        config_fields=config_fields, chars_col=self.chars_col)

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
            img_url = self.get_page_img(self.page)
            if not self.get_query_argument('step', '') and self.steps['current'] == 'select' and self.page.get('cmp'):
                self.steps.update(dict(current='proof', is_first=False, is_last=True, prev='select', next=None))

            if self.steps['current'] == 'select':
                return self.render('page_task_select.html', page=self.page, img_url=img_url,
                                   ocr=self.get_txt('ocr'), cmp=self.get_txt('cmp'))
            else:
                texts, doubts = self.get_cmp_data()
                text_dict = {t[1]: t for t in texts}
                cmp_data = self.prop(self.task, 'result.txt_html')
                text_fields = self.prop(self.task, 'result.text_fields')
                if not cmp_data:
                    text_fields = [t[1] for t in texts]
                    cmp_data = self.diff(*[t[0] for t in texts])
                    cmp_data = to_basestring(TextArea(self).render(cmp_data))
                return self.render('page_task_text.html', page=self.page, img_url=img_url, texts=texts,
                                   text_dict=text_dict, doubts=doubts, cmp_data=cmp_data,
                                   text_fields=text_fields)

        except Exception as error:
            return self.send_db_error(error)


class TaskTextReviewHandler(PageHandler):
    URL = ['/task/(text_review|text_hard)/@task_id',
           '/task/do/(text_review|text_hard)/@task_id',
           '/task/browse/(text_review|text_hard)/@task_id',
           '/task/update/(text_review|text_hard)/@task_id']

    def get(self, task_type, task_id):
        """ 文字审定、难字处理页面"""
        try:
            self.texts, self.doubts = self.get_cmp_data()
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
            self.texts, self.doubts = self.get_cmp_data()
            cmp_data, text = self.page.get('txt_html') or '', self.page.get('text') or ''
            if not cmp_data and not text:
                self.send_error_response(e.no_object, message='没有找到审定文本')

            if not cmp_data and text:
                cmp_data = self.diff(text)
                cmp_data = to_basestring(TextArea(self).render(cmp_data))

            self.render('page_task_text.html', cmp_data=cmp_data)

        except Exception as error:
            return self.send_db_error(error)


class PageBrowseHandler(PageHandler):
    URL = '/page/browse/@page_name'

    def get(self, page_name):
        """ 浏览页面数据"""

        edit_fields = [
            {'id': 'name', 'name': '页编码', 'readonly': True},
            {'id': 'box_ready', 'name': '切分就绪', 'input_type': 'radio', 'options': ['是', '否']},
            {'id': 'layout', 'name': '图片结构', 'input_type': 'radio', 'options': self.layouts},
            {'id': 'source', 'name': '分　　类'},
            {'id': 'level-box', 'name': '切分等级'},
            {'id': 'level-text', 'name': '文本等级'},
        ]
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            condition = self.get_page_search_condition(self.request.query)[0]
            to = self.get_query_argument('to', '')
            if to == 'next':
                condition['page_code'] = {'$gt': page['page_code']}
                page = self.db.page.find_one(condition, sort=[('page_code', 1)])
            elif to == 'prev':
                condition['page_code'] = {'$lt': page['page_code']}
                page = self.db.page.find_one(condition, sort=[('page_code', -1)])
            if not page:
                message = '没有找到页面%s的%s' % (page_name, '上一页' if to == 'prev' else '下一页')
                return self.send_error_response(e.no_object, message=message)

            img_url = self.get_web_img(page['name'])
            chars_col = self.get_chars_col(page['chars'])
            btn_config = json_util.loads(self.get_secure_cookie('data_page_button') or '{}')
            info = {f['id']: self.prop(page, f['id'].replace('-', '.'), '') for f in edit_fields}
            labels = dict(text='审定文本', ocr='字框OCR', ocr_col='列框OCR')
            texts = [(page.get(f), f, labels.get(f)) for f in ['ocr', 'ocr_col', 'text'] if page.get(f)]
            self.render('page_browse.html', page=page, chars_col=chars_col, btn_config=btn_config,
                        texts=texts, info=info, edit_fields=edit_fields, img_url=img_url)

        except Exception as error:
            return self.send_db_error(error)


class PageViewHandler(PageHandler):
    URL = '/page/@page_name'

    def get(self, page_name):
        """ 查看页面数据"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)

            texts = self.get_all_txt(page)
            img_url = self.get_web_img(page['name'])
            chars_col = self.get_chars_col(page['chars'])
            cid = self.get_query_argument('char_id', '').split('_')[-1]
            txt_off = self.get_query_argument('txt', None) == 'off'
            self.render('page_view.html', texts=texts, img_url=img_url, page=page, chars_col=chars_col,
                        txt_off=txt_off, cur_cid=cid)

        except Exception as error:
            return self.send_db_error(error)


class TextArea(UIModule):
    """文字校对的文字区"""

    def render(self, cmp_data):
        return self.render_string('page_text_area.html', blocks=cmp_data)
