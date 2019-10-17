#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经数据管理
@time: 2019/3/13
"""
from controller.base import BaseHandler


class SearchCbetaHandler(BaseHandler):
    URL = '/search/cbeta'

    def get(self):
        """ 检索cbeta库 """
        self.render('search_cbeta.html')
