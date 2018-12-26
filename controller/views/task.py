#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务大厅和我的任务
@time: 2018/12/26
"""

from tornado.web import authenticated
from controller.base import BaseHandler


class ChooseCharProofHandler(BaseHandler):
    URL = '/dzj_char.html'

    @authenticated
    def get(self):
        """ 任务大厅-文字校对 """
        self.render('dzj_char.html')


class MyCharProofHandler(BaseHandler):
    URL = '/dzj_char_history.html'

    @authenticated
    def get(self):
        """ 我的任务-文字校对 """
        self.render('dzj_char_history.html')


class CharProofDetailHandler(BaseHandler):
    URL = '/dzj_char_detail.html'

    @authenticated
    def get(self):
        """ 任务大厅-文字校对 """
        self.render('dzj_char_detail.html')
