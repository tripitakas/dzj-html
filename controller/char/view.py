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
            self.render('char_browse.html', docs=docs, pager=pager, q=q, order=order)

        except Exception as error:
            return self.send_db_error(error)
