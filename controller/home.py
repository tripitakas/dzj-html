#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 首页
@time: 2018/6/23
"""

from tornado.web import authenticated
from controller.base import BaseHandler
from os import path


class InvalidPageHandler(BaseHandler):
    def get(self):
        if '/api/' in self.request.path:
            self.set_status(404, reason='Not found')
            return self.finish()
        if path.exists(path.join(self.get_template_path(), self.request.path.replace('/', ''))):
            return self.render(self.request.path.replace('/', ''))
        self.render('_404.html')


class HomeHandler(BaseHandler):
    URL = ['/', '/dzj_home.html']

    @authenticated
    def get(self):
        """ 首页 """
        self.render('dzj_home.html')
