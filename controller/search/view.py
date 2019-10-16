#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经数据管理
@time: 2019/3/13
"""
from controller.base import BaseHandler

class DataSearchCbetaHandler(BaseHandler):
    URL = '/data/cbeta_search'

    def get(self):
        """ 检索cbeta库 """
        self.render('data_cbeta_search.html')
