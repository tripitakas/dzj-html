#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 首页
@time: 2018/6/23
"""

from tornado.web import authenticated
from controller.base import BaseHandler


class HomeHandler(BaseHandler):
    URL = ['/', '/dzj_home.html']

    @authenticated
    def get(self):
        """ 首页 """
        self.render('dzj_home.html')
