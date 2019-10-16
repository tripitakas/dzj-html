#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经数据管理
@time: 2019/3/13
"""
from controller.base import BaseHandler


class DataPunctuationHandler(BaseHandler):
    URL = '/data/punctuation'

    def get(self):
        """ 自动标点 """
        self.render('data_punctuation.html')
