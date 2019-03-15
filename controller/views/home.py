#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 首页
@time: 2018/6/23
"""

from tornado.web import authenticated
from controller.base.task import TaskHandler


class HomeHandler(TaskHandler):
    URL = '/home'

    @authenticated
    def get(self):
        """ 首页 """
        self.render('home.html')
