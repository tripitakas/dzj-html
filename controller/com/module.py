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
from controller import helper as h


class ComLeft(UIModule):
    def render(self, active_id=''):
        def is_enabled(module):
            return module not in h.prop(self.handler.config, 'modules.disabled', '')

        can_access = self.handler.can_access

        items = [
            dict(name='首页', icon='icon-home', link='/home'),
            dict(name='大藏经', icon='icon-tripitaka', link='/tripitaka/list'),
            dict(name='任务大厅', icon='icon-task-lobby', id='task-lobby', sub_items=[
                dict(name='切分校对', icon='icon-subitem', link='/task/lobby/cut_proof'),
                dict(name='切分审定', icon='icon-subitem', link='/task/lobby/cut_review'),
                dict(name='聚类校对', icon='icon-subitem', link='/task/lobby/cluster_proof'),
                dict(name='聚类审定', icon='icon-subitem', link='/task/lobby/cluster_review'),
                dict(name='异体校对', icon='icon-subitem', link='/task/lobby/variant_proof'),
                dict(name='异体审定', icon='icon-subitem', link='/task/lobby/variant_review'),
                dict(name='文字校对', icon='icon-subitem', link='/task/lobby/txt_proof'),
                dict(name='文字审定', icon='icon-subitem', link='/task/lobby/txt_review'),
            ]),
            dict(name='我的任务', icon='icon-task-my', id='task-my', sub_items=[
                dict(name='切分校对', icon='icon-subitem', link='/task/my/cut_proof'),
                dict(name='切分审定', icon='icon-subitem', link='/task/my/cut_review'),
                dict(name='聚类校对', icon='icon-subitem', link='/task/my/cluster_proof'),
                dict(name='聚类审定', icon='icon-subitem', link='/task/my/cluster_review'),
                dict(name='异体校对', icon='icon-subitem', link='/task/my/variant_proof'),
                dict(name='异体审定', icon='icon-subitem', link='/task/my/variant_review'),
                dict(name='文字校对', icon='icon-subitem', link='/task/my/txt_proof'),
                dict(name='文字审定', icon='icon-subitem', link='/task/my/txt_review'),
            ]),
            dict(name='任务管理', icon='icon-task-admin', id='task-admin', sub_items=[
                dict(name='页任务', icon='icon-subitem', link='/page/task/list'),
                dict(name='字任务', icon='icon-subitem', link='/char/task/list'),
            ]),
            dict(name='数据管理', icon='icon-data', id='data', sub_items=[
                dict(name='藏数据', icon='icon-subitem', link='/data/tripitaka'),
                dict(name='册数据', icon='icon-subitem', link='/data/volume'),
                dict(name='经数据', icon='icon-subitem', link='/data/sutra'),
                dict(name='卷数据', icon='icon-subitem', link='/data/reel'),
                dict(name='页数据', icon='icon-subitem', link='/page/list'),
                dict(name='字数据', icon='icon-subitem', link='/char/list'),
                dict(name='异体字', icon='icon-subitem', link='/data/variant'),
            ]),
            dict(name='文章管理', icon='icon-article', link='/article/admin'),
            dict(name='人员管理', icon='icon-users', id='user', sub_items=[
                dict(name='用户管理', icon='icon-subitem', link='/user/admin'),
                dict(name='授权管理', icon='icon-subitem', link='/user/role'),
            ]),
            dict(name='系统管理', icon='icon-admin', id='sys', sub_items=[
                dict(name='脚本管理', icon='icon-subitem', link='/sys/script'),
                dict(name='脚本日志', icon='icon-subitem', link='/sys/oplog'),
                dict(name='操作日志', icon='icon-subitem', link='/sys/log'),
            ]),
            dict(name='相关工具', icon='icon-tool', id='tool', sub_items=[
                dict(name='自动标点', icon='icon-subitem', link='/com/punctuate'),
                dict(name='全文检索', icon='icon-subitem', link='/com/search'),
            ]),
            dict(name='帮助中心', icon='icon-info', link='/help'),
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

        return self.render_string('_left.html', display_items=display_items, active_id=active_id)


class ComHead(UIModule):
    def render(self):
        return self.render_string('_head.html')


class Pager(UIModule):
    def get_page_uri(self, page_no):
        page_no = str(page_no)
        uri = self.request.uri
        if 'page=' in uri:
            uri = re.sub(r'page=\d+&', 'page=' + page_no + '&', uri)
            uri = re.sub(r'page=\d+$', 'page=' + page_no, uri)
            return uri
        elif '?' in uri:
            return uri + '&page=' + page_no
        else:
            return uri + '?page=' + page_no

    def render(self, pager):
        if not isinstance(pager, dict):
            pager = dict(cur_page=0, doc_count=0)
        if isinstance(pager, dict) and 'cur_page' in pager and 'doc_count' in pager:
            conf = self.handler.application.config
            pager['page_size'] = h.prop(pager, 'page_size', h.prop(conf, 'pager.page_size'))  # 每页显示多少条记录
            pager['page_count'] = math.ceil(pager['doc_count'] / pager['page_size'])  # 一共有多少页
            pager['display_count'] = h.prop(conf, 'pager.display_count')  # pager导航条中显示多少个页码
            # 计算显示哪些页码
            gap, if_left, cur_page = int(pager['display_count'] / 2), int(pager['display_count']) % 2, pager['cur_page']
            start, end = cur_page - gap, cur_page + gap - 1 + if_left
            offset = 1 - start if start < 1 else pager['page_count'] - end if pager['page_count'] < end else 0
            start, end = start + offset, end + offset
            start = 1 if start < 1 else start
            end = pager['page_count'] if end > pager['page_count'] else end
            pager['display_range'] = range(start, end + 1)
            pager['options'] = sorted(list({10, 30, 50, 100, 500, pager['page_size']}))

        return self.render_string('_pager.html', get_page_uri=self.get_page_uri, **pager)


class ComTable(UIModule):

    def render(self, docs, table_fields, actions, info_fields=None, hide_fields=None, order='',
               pack=None, format_value=None):
        pack = dumps if not pack else pack
        hide_fields = [] if hide_fields is None else hide_fields
        format_value = h.format_value if not format_value else format_value
        info_fields = [d['id'] for d in table_fields] if info_fields is None else info_fields
        return self.render_string(
            '_table.html', docs=docs, order=order, actions=actions, table_fields=table_fields,
            info_fields=info_fields, hide_fields=hide_fields, format_value=format_value,
            pack=pack, prop=h.prop
        )


class ComModal(UIModule):
    def render(self, modal_fields, id='', title='', buttons=None):
        buttons = [('modal-cancel', '取消'), ('modal-confirm', '确定')] if buttons is None else buttons
        return self.render_string('_modal.html', modal_fields=modal_fields, id=id, title=title, buttons=buttons)


class ReturnModal(UIModule):
    def render(self):
        buttons = [('modal-cancel', '取消'), ('modal-confirm', '确定')]
        modal_fields = [{'id': 'return_reason', 'name': '退回理由', 'input_type': 'textarea'}]
        return self.render_string('_modal.html', modal_fields=modal_fields, id='returnModal', title='退回任务',
                                  buttons=buttons)


class DoubtModal(UIModule):
    def render(self):
        buttons = [('modal-cancel', '取消'), ('modal-confirm', '确定')]
        modal_fields = [
            {'id': 'doubt_input', 'name': '存疑文本'},
            {'id': 'doubt_reason', 'name': '存疑理由', 'input_type': 'textarea'}
        ]
        return self.render_string('_modal.html', modal_fields=modal_fields, id='doubtModal', title='存疑',
                                  buttons=buttons)


class TaskRemarkModal(UIModule):
    def render(self):
        buttons = [('modal-cancel', '取消'), ('modal-confirm', '确定')]
        modal_fields = [
            {'id': 'is_sample', 'name': '示例任务', 'input_type': 'radio', 'options': ['是', '否']},
            {'id': 'remark', 'name': '备注内容'},
            {'id': 'options', 'name': '　', 'input_type': 'radio', 'options': ['没问题', '还可以', '不合要求']},
        ]
        return self.render_string('_modal.html', modal_fields=modal_fields, id='remarkModal', title='备注',
                                  buttons=buttons)


class PageRemarkModal(UIModule):
    def render(self):
        buttons = [('modal-cancel', '取消'), ('modal-confirm', '确定')]
        modal_fields = [
            {'id': 'fields', 'name': '备注字段', 'input_type': 'radio', 'options': ['切分', '文本']},
            {'id': 'remark', 'name': '备注内容'},
            {'id': 'options', 'name': '　', 'input_type': 'radio', 'options': ['没问题', '还可以', '不合要求']},
        ]
        return self.render_string('_modal.html', modal_fields=modal_fields, id='remarkModal', title='备注',
                                  buttons=buttons)


class TaskConfigModal(UIModule):
    def render(self, config_fields=None):
        title = '配置项'
        buttons = [('modal-cancel', '取消'), ('modal-confirm', '确定')]
        fields = [{'id': 'auto-pick', 'name': '提交后自动领新任务', 'input_type': 'radio', 'options': ['是', '否']}]
        return self.render_string('_config.html', modal_fields=config_fields or fields, id='taskConfigModal',
                                  title=title, buttons=buttons)
