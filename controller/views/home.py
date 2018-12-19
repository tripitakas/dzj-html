#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 首页
@time: 2018/6/23
"""

from controller.public.base import BaseHandler
from tornado.web import authenticated


class HomeHandler(BaseHandler):
    URL = ['/', '/dzj_home.html']

    @authenticated
    def get(self):
        """ 首页 """
        self.render('dzj_home.html')
