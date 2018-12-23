#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: UI模块
@file: modules.py
@time: 2018/12/22
"""
from tornado.web import UIModule


class DemoPanel(UIModule):
    def render(self, owner=False):
        return self.render_string('demo.html', owner=owner)
