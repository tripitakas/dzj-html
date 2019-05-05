#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: UI模块
@file: modules.py
@time: 2018/12/22
"""
from tornado.web import UIModule
import math


class CommonLeft(UIModule):
    def render(self, title='', sub=''):
        return self.render_string('common_left.html', title=title, sub=sub)


class CommonHead(UIModule):
    def render(self):
        return self.render_string('common_head.html')


class Pager(UIModule):
    def render(self, pager):
        assert isinstance(pager, dict) and 'cur_page' in pager and 'item_count' in pager

        conf = self.handler.application.config['pager']
        pager['page_size'] = pager.get('page_size', conf['page_size'])  # 每页显示多少条记录
        pager['page_count'] = math.ceil(pager['item_count'] / pager['page_size'])  # 一共有多少页
        pager['display_count'] = conf['display_count']  # pager导航条中显示多少个页码
        pager['path'] = self.request.path  # 当前path

        gap, if_left, cur_page = int(pager['display_count'] / 2), int(pager['display_count']) % 2, pager['cur_page']
        start, end = cur_page - gap, cur_page + gap - 1 + if_left
        offset = 1 - start if start < 1 else pager['page_count'] - end if pager['page_count'] < end else 0
        start, end = start + offset, end + offset
        start = 1 if start < 1 else start
        end = pager['page_count'] if end > pager['page_count'] else end
        pager['display_range'] = range(start, end + 1)

        return self.render_string('_pager.html', pager=pager)
