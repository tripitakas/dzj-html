#!/usr/bin/env python
# -*- coding: utf-8 -*-
from controller.data.data import Char
from controller.base import BaseHandler


class CharBrowseHandler(BaseHandler, Char):
    URL = '/char/browse'
    search_fields = ['id', 'source', 'ocr', 'txt']

    def get(self):
        """ 浏览字图"""
        try:
            condition = Char.get_char_search_condition(self.request.query)[0]
            docs, pager, q, order = self.find_by_page(self, condition)
            columns, pages = {}, {}
            for c in docs:
                column_cid = '%s_%s' % (c['page_name'], c['column_cid'])
                if not columns.get(column_cid):
                    page = pages[c['page_name']] = pages.get(c['page_name']) or self.db.page.find_one(
                        {'name': c['page_name']}) or {'_': 1}
                    col = [col for col in page.get('columns', []) if col['cid'] == c['column_cid']]
                    if col:
                        col = col[0]
                        columns[column_cid] = dict(x=col['x'], y=col['y'], w=col['w'], h=col['h'])
            self.render('char_browse.html', docs=docs, pager=pager, q=q, order=order, columns=columns)

        except Exception as error:
            return self.send_db_error(error)
