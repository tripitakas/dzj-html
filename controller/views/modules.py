#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: UI模块
@file: modules.py
@time: 2018/12/22
"""
from tornado.web import UIModule


class CommonLeft(UIModule):
    def render(self, title='', sub=''):
        return self.render_string('common_left.html', title=title, sub=sub)


class CommonHead(UIModule):
    def render(self):
        return self.render_string('common_head.html')
