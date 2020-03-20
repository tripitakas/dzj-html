#!/usr/bin/env python
# -*- coding: utf-8 -*-
from controller import helper as h
from controller.data.data import Char
from controller.base import BaseHandler


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
                if not d['column']:
                    print('%s no column' % d['name'])
                    continue
                column_name = '%s_%s' % (d['page_name'], d['column']['cid'])
                d['column']['hash'] = h.md5_encode(column_name, self.get_config('web_img.salt'))
                if not column_url:
                    column_url = self.get_web_img(column_name, 'column')
            self.render('char_browse.html', docs=docs, pager=pager, q=q, order=order,
                        column_url=column_url, chars={str(d['_id']): d for d in docs})

        except Exception as error:
            return self.send_db_error(error)
