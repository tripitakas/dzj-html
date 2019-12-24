#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: UI模块
@file: modules.py
@time: 2018/12/22
"""
import re
import math
from bson.json_util import dumps
from tornado.web import UIModule
from controller.helper import prop


class ComLeft(UIModule):
    def render(self, title='', sub=''):
        def is_enabled(module):
            return module not in prop(self.handler.config, 'modules.disabled', '')

        can_access = self.handler.can_access

        items = [
            dict(name='首页', icon='icon_home', link='/home'),
            dict(name='大藏经', icon='icon_tripitaka', link='/tripitaka/list'),
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
                dict(name='导入图片', icon='icon_subitem', link='/task/admin/import_image'),
                dict(name='上传云端', icon='icon_subitem', link='/task/admin/upload_cloud'),
                dict(name='OCR字框', icon='icon_subitem', link='/task/admin/ocr_box'),
                dict(name='切分校对', icon='icon_subitem', link='/task/admin/cut_proof'),
                dict(name='切分审定', icon='icon_subitem', link='/task/admin/cut_review'),
                dict(name='OCR文字', icon='icon_subitem', link='/task/admin/ocr_text'),
                dict(name='文字校对', icon='icon_subitem', link='/task/admin/text_proof'),
                dict(name='文字审定', icon='icon_subitem', link='/task/admin/text_review'),
                dict(name='难字校对', icon='icon_subitem', link='/task/admin/text_hard'),
            ]),
            dict(name='数据管理', icon='icon_data', id='data', sub_items=[
                dict(name='藏数据', icon='icon_subitem', link='/data/tripitaka'),
                dict(name='册数据', icon='icon_subitem', link='/data/volume'),
                dict(name='经数据', icon='icon_subitem', link='/data/sutra'),
                dict(name='卷数据', icon='icon_subitem', link='/data/reel'),
                dict(name='页数据', icon='icon_subitem', link='/data/page'),
            ]),
            dict(name='人员管理', icon='icon_user', id='user', sub_items=[
                dict(name='用户管理', icon='icon_subitem', link='/user/admin'),
                dict(name='授权管理', icon='icon_subitem', link='/user/admin/role'),
                dict(name='数据统计', icon='icon_subitem', link='/user/admin/statistic'),
            ]),
            dict(name='系统管理', icon='icon_admin', id='admin', sub_items=[
                dict(name='文章管理', icon='icon_subitem', link='/article'),
                dict(name='脚本管理', icon='icon_subitem', link='/admin/script'),
            ]),
            dict(name='相关工具', icon='icon_tool', id='tool', sub_items=[
                dict(name='自动标点', icon='icon_subitem', link='/tool/punctuate'),
                dict(name='CBeta检索', icon='icon_subitem', link='/tool/search'),
            ]),
            dict(name='帮助中心', icon='icon_help', link='/help'),
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
                checked = lambda i: is_enabled(i.get('name')) and i.get('link') and can_access(i['link'])
                sub_items = [i for i in item['sub_items'] if checked(i)]
                if sub_items:
                    for _item in sub_items:
                        _item['id'] = re.sub('[/_]', '-', _item['link'][1:])
                    item['sub_items'] = sub_items
                    display_items.append(item)

        return self.render_string('com_left.html', display_items=display_items, active_name='')


class ComHead(UIModule):
    def render(self):
        return self.render_string('com_head.html')


class Pager(UIModule):
    def render(self, pager):
        if not isinstance(pager, dict):
            pager = dict(cur_page=0, doc_count=0)
        if isinstance(pager, dict) and 'cur_page' in pager and 'doc_count' in pager:
            conf = self.handler.application.config
            pager['page_size'] = prop(pager, 'page_size', prop(conf, 'pager.page_size'))  # 每页显示多少条记录
            pager['pager_count'] = math.ceil(pager['doc_count'] / pager['page_size'])  # 一共有多少页
            pager['display_count'] = prop(conf, 'pager.display_count')  # pager导航条中显示多少个页码
            pager['uri'] = re.sub(r'[?&]page=\d+', '', self.request.uri)  # 当前path
            pager['uri'] = re.sub(r'[?&]page_size=\d+', '', pager['uri'])  # 当前path
            pager['link'] = '&' if '?' in pager['uri'] else '?'  # 当前path
            gap, if_left, cur_page = int(pager['display_count'] / 2), int(pager['display_count']) % 2, pager['cur_page']
            start, end = cur_page - gap, cur_page + gap - 1 + if_left
            offset = 1 - start if start < 1 else pager['pager_count'] - end if pager['pager_count'] < end else 0
            start, end = start + offset, end + offset
            start = 1 if start < 1 else start
            end = pager['pager_count'] if end > pager['pager_count'] else end
            pager['display_range'] = range(start, end + 1)

        return self.render_string('com_pager.html', **pager)


class ComTable(UIModule):
    def render(self, docs, table_fields, actions, info_fields=None, order=''):
        info_fields = [d['id'] for d in table_fields]
        return self.render_string('com_table.html', dumps=dumps, docs=docs, table_fields=table_fields,
                                  info_fields=info_fields, actions=actions, order=order)


class ComModal(UIModule):
    def render(self, modal_fields, id='', title=''):
        return self.render_string('com_modal.html', modal_fields=modal_fields, id=id, title=title)
