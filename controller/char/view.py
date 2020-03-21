#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .base import CharHandler
from controller import helper as h
from controller.data.data import Char
from controller.base import BaseHandler
from controller.task.base import TaskHandler


class CharBrowseHandler(BaseHandler, Char):
    URL = '/char/browse'

    page_size = 50

    def get(self):
        """ 浏览字图"""
        try:
            condition = Char.get_char_search_condition(self.request.query)[0]
            docs, pager, q, order = self.find_by_page(self, condition)
            column_url = ''
            for d in docs:
                column_name = '%s_%s' % (d['page_name'], self.prop(d, 'column.cid'))
                d['column']['hash'] = h.md5_encode(column_name, self.get_config('web_img.salt'))
                if not column_url:
                    column_url = self.get_web_img(column_name, 'column')
            self.render('char_browse.html', docs=docs, pager=pager, q=q, order=order,
                        column_url=column_url, chars={str(d['_id']): d for d in docs})

        except Exception as error:
            return self.send_db_error(error)


class TaskCharProofHandler(CharHandler):
    URL = ['/task/char_proof/@task_id',
           '/task/do/char_proof/@task_id',
           '/task/browse/char_proof/@task_id',
           '/task/update/char_proof/@task_id']

    page_size = 50

    def get(self, task_id):
        """ 聚类校对页面"""
        try:
            condition = dict(batch=self.task['batch'], ocr_txt=self.prop(self.task, 'input.ocr_txt'))
            docs, pager, q, order = Char.find_by_page(self, condition, default_order='cc')
            column_url = ''
            for d in docs:
                column_name = '%s_%s' % (d['page_name'], self.prop(d, 'column.cid'))
                d['column']['hash'] = h.md5_encode(column_name, self.get_config('web_img.salt'))
                if not column_url:
                    column_url = self.get_web_img(column_name, 'column')
            self.render('char_cluster_proof.html', docs=docs, pager=pager, q=q, order=order,
                        column_url=column_url, chars={str(d['_id']): d for d in docs})

        except Exception as error:
            return self.send_db_error(error)
