#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 首页
@time: 2018/6/23
"""

from tornado.web import authenticated
from controller.base import BaseHandler


class InvalidPageHandler(BaseHandler):
    def get(self):
        if '/api/' in self.request.path:
            self.set_status(404, reason='Not found')
            return self.finish()
        self.render('_404.html')


class HomeHandler(BaseHandler):
    URL = r'/'

    def get(self):
        """ 首页 """
        self.render('index.html')
