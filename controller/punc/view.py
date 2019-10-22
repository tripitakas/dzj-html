#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经数据管理
@time: 2019/3/13
"""
from controller.base import BaseHandler


class PunctuationHandler(BaseHandler):
    URL = '/punc/punctuate'

    def get(self):
        """ 自动标点 """
        self.render('punc_punctuate.html')
