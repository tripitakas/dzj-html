#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: UI模块
@file: modules.py
@time: 2018/12/22
"""
import re
import math
from tornado.web import UIModule


class CommonLeft(UIModule):
    def render(self, title='', sub=''):
        def is_enabled(module):
            if 'disable_modules' in self.handler.config and self.handler.config['disable_modules']:
                return module not in self.handler.config['disable_modules']
            return True

        can_access = self.handler.can_access

        items = [
            dict(name='首页', icon='icon_home', link='/home'),
            dict(name='CBETA', icon='icon_rs', link='/cbeta'),
            dict(name='大藏经', icon='icon_tripitaka', link='/tripitakas'),
            dict(name='任务大厅', icon='icon_task_lobby', id='task-lobby', sub_items=[
                dict(name='切分校对', icon='icon_subitem', link='/task/lobby/cut_proof'),
                dict(name='切分审定', icon='icon_subitem', link='/task/lobby/cut_review'),
                dict(name='文字校对', icon='icon_subitem', link='/task/lobby/text_proof'),
                dict(name='文字审定', icon='icon_subitem', link='/task/lobby/text_review'),
                dict(name='难字审定', icon='icon_subitem', link='/task/lobby/text_hard'),
            ]),
            dict(name='我的任务', icon='icon_my_task', id='task-my', sub_items=[
                dict(name='切分校对', icon='icon_subitem', link='/task/my/cut_proof'),
                dict(name='切分审定', icon='icon_subitem', link='/task/my/cut_review'),
                dict(name='文字校对', icon='icon_subitem', link='/task/my/text_proof'),
                dict(name='文字审定', icon='icon_subitem', link='/task/my/text_review'),
                dict(name='难字审定', icon='icon_subitem', link='/task/my/text_hard'),
            ]),
            dict(name='任务管理', icon='icon_task_admin', id='task-admin', sub_items=[
                dict(name='任务状态', icon='icon_subitem', link='/task/admin/task_status'),
                dict(name='切分校对', icon='icon_subitem', link='/task/admin/cut_proof'),
                dict(name='切分审定', icon='icon_subitem', link='/task/admin/cut_review'),
                dict(name='文字校对', icon='icon_subitem', link='/task/admin/text_proof_1'),
                dict(name='文字审定', icon='icon_subitem', link='/task/admin/text_review'),
                dict(name='难字审定', icon='icon_subitem', link='/task/admin/text_hard'),
            ]),
            dict(name='人员管理', icon='icon_user', id='user', sub_items=[
                dict(name='用户管理', icon='icon_subitem', link='/user/admin'),
                dict(name='授权管理', icon='icon_subitem', link='/user/role'),
                dict(name='数据统计', icon='icon_subitem', link='/user/statistic'),
            ]),
            dict(name='数据管理', icon='icon_data', id='data', sub_items=[
                dict(name='藏数据', icon='icon_subitem', link='/data/tripitaka'),
                dict(name='册数据', icon='icon_subitem', link='/data/volume'),
                dict(name='经数据', icon='icon_subitem', link='/data/sutra'),
                dict(name='卷数据', icon='icon_subitem', link='/data/reel'),
                dict(name='页数据', icon='icon_subitem', link='/data/page'),
            ]),
            dict(name='相关工具', icon='icon_tool', id='tool', sub_items=[
                dict(name='文字识别', icon='icon_subitem', link='/data/ocr'),
                dict(name='自动标点', icon='icon_subitem', link='/data/punctuation'),
                dict(name='CBETA检索', icon='icon_subitem', link='/data/cbeta_search'),
            ]),
            dict(name='帮助文档', icon='icon_help', link='/help'),
        ]

        # 计算当前用户有权访问的item
        display_items = []
        for item in items:
            if not is_enabled(item.get('name')):
                continue
            if item.get('link') and can_access(item['link']):
                item['id'] = re.sub('[/_]', '-', item['link'][1:])
                display_items.append(item)
            if item.get('sub_items'):
                sub_items = [i for i in item['sub_items'] if
                             is_enabled(i.get('name')) and i.get('link') and can_access(i['link'])]
                if sub_items:
                    for _item in sub_items:
                        _item['id'] = re.sub('[/_]', '-', _item['link'][1:])
                    item['sub_items'] = sub_items
                    display_items.append(item)

        return self.render_string('common_left.html', title=title, sub=sub, display_items=display_items)


class CommonHead(UIModule):
    def render(self):
        return self.render_string('common_head.html')


class Pager(UIModule):
    def render(self, pager):
        if not isinstance(pager, dict):
            pager = dict(cur_page=0, item_count=0)
        if isinstance(pager, dict) and 'cur_page' in pager and 'item_count' in pager:
            conf = self.handler.application.config['pager']
            pager['page_size'] = pager.get('page_size', conf['page_size'])  # 每页显示多少条记录
            pager['page_count'] = math.ceil(pager['item_count'] / pager['page_size'])  # 一共有多少页
            pager['display_count'] = conf['display_count']  # pager导航条中显示多少个页码
            pager['path'] = re.sub(r'[?&]page=\d+', '', self.request.uri)  # 当前path
            pager['link'] = '&' if '?' in pager['path'] else '?'  # 当前path
            gap, if_left, cur_page = int(pager['display_count'] / 2), int(pager['display_count']) % 2, pager['cur_page']
            start, end = cur_page - gap, cur_page + gap - 1 + if_left
            offset = 1 - start if start < 1 else pager['page_count'] - end if pager['page_count'] < end else 0
            start, end = start + offset, end + offset
            start = 1 if start < 1 else start
            end = pager['page_count'] if end > pager['page_count'] else end
            pager['display_range'] = range(start, end + 1)

        return self.render_string('_pager.html', pager=pager)
