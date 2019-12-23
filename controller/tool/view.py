#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经数据管理
@time: 2019/3/13
"""
from controller.base import BaseHandler


class SearchCbetaHandler(BaseHandler):
    URL = '/tool/search'

    def get(self):
        """ 检索cbeta库 """
        self.render('tool_search.html')


class PunctuationHandler(BaseHandler):
    URL = '/tool/punctuate'

    def get(self):
        """ 自动标点 """
        self.render('tool_punctuate.html')
