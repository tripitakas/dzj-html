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
    URL = ['/task/cluster_proof/@task_id',
           '/task/do/cluster_proof/@task_id',
           '/task/browse/cluster_proof/@task_id',
           '/task/update/cluster_proof/@task_id']

    page_size = 50
    txt_types = {'': '没问题', 'M': '模糊或残损', 'N': '不确定', '*': '不认识'}

    def get(self, task_id):
        """ 聚类校对页面"""
        try:
            params = self.task['params']
            ocr_txts = [c['ocr_txt'] for c in params]
            cond = {'source': params[0]['source'], 'ocr_txt': {'$in': ocr_txts}}
            # 统计字字种
            counts = list(self.db.char.aggregate([
                {'$match': cond}, {'$group': {'_id': '$txt', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
            ]))
            txts = [c['_id'] for c in counts]
            # 设置当前正字
            txt = self.get_query_argument('txt', txts[0])
            cond.update({'txt': txt})
            # 查找单字数据
            docs, pager, q, order = Char.find_by_page(self, cond, default_order='cc')
            column_url = ''
            for d in docs:
                column_name = '%s_%s' % (d['page_name'], self.prop(d, 'column.cid'))
                d['column']['hash'] = h.md5_encode(column_name, self.get_config('web_img.salt'))
                if not column_url:
                    column_url = self.get_web_img(column_name, 'column')
            self.render('char_task_cluster.html', docs=docs, pager=pager, q=q, order=order,
                        char_count=self.task.get('char_count'), ocr_txts=ocr_txts,
                        txts=txts, txt=txt, column_url=column_url,
                        chars={str(d['_id']): d for d in docs})

        except Exception as error:
            return self.send_db_error(error)
