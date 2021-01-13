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
from controller.char.char import Char
from controller.task.task import Task
from controller.page.base import PageHandler as Ph


class ComLeft(UIModule):
    def render(self, active_id=''):
        def is_enabled(module):
            return module not in h.prop(self.handler.config, 'modules.disabled', '')

        # 默认左侧菜单项
        base_items = [
            dict(name='首页', icon='icon-home', link='/home'),
            dict(name='大藏经', icon='icon-tripitaka', link='/tripitaka/list'),
            dict(name='任务大厅', icon='icon-task-lobby', sub_items=[
                dict(name='切分校对', icon='icon-subitem', link='/task/lobby/cut_proof'),
                dict(name='切分审定', icon='icon-subitem', link='/task/lobby/cut_review'),
                dict(name='文字校对', icon='icon-subitem', link='/task/lobby/text_proof'),
                dict(name='文字审定', icon='icon-subitem', link='/task/lobby/text_review'),
                dict(name='聚类校对', icon='icon-subitem', link='/task/lobby/cluster_proof'),
                dict(name='聚类审定', icon='icon-subitem', link='/task/lobby/cluster_review'),
            ]),
            dict(name='我的任务', icon='icon-task-my', sub_items=[
                dict(name='切分校对', icon='icon-subitem', link='/task/my/cut_proof'),
                dict(name='切分审定', icon='icon-subitem', link='/task/my/cut_review'),
                dict(name='文字校对', icon='icon-subitem', link='/task/my/text_proof'),
                dict(name='文字审定', icon='icon-subitem', link='/task/my/text_review'),
                dict(name='聚类校对', icon='icon-subitem', link='/task/my/cluster_proof'),
                dict(name='聚类审定', icon='icon-subitem', link='/task/my/cluster_review'),
            ]),
            dict(name='任务管理', icon='icon-task-admin', sub_items=[
                dict(name='页任务', icon='icon-subitem', link='/page/task/list'),
                dict(name='字任务', icon='icon-subitem', link='/char/task/list'),

            ]),
            dict(name='数据管理', icon='icon-data', sub_items=[
                dict(name='导图片', icon='icon-subitem', link='/data/image'),
                dict(name='藏数据', icon='icon-subitem', link='/data/tripitaka'),
                dict(name='册数据', icon='icon-subitem', link='/data/volume'),
                dict(name='经数据', icon='icon-subitem', link='/data/sutra'),
                dict(name='卷数据', icon='icon-subitem', link='/data/reel'),
                dict(name='页数据', icon='icon-subitem', link='/page/list'),
                dict(name='字数据', icon='icon-subitem', link='/char/list'),
                dict(name='异体字', icon='icon-subitem', link='/data/variant'),
            ]),
            dict(name='人员管理', icon='icon-users', id='user', sub_items=[
                dict(name='指派批次', icon='icon-subitem', link='/user/task_batch'),
                dict(name='用户管理', icon='icon-subitem', link='/user/admin'),
                dict(name='授权管理', icon='icon-subitem', link='/user/roles'),
            ]),
            dict(name='系统管理', icon='icon-admin', sub_items=[
                dict(name='脚本管理', icon='icon-subitem', link='/sys/script'),
                dict(name='脚本日志', icon='icon-subitem', link='/sys/oplog'),
                dict(name='操作日志', icon='icon-subitem', link='/sys/log'),
            ]),
            dict(name='文章管理', icon='icon-article', link='/article/admin'),
            dict(name='帮助中心', icon='icon-help', link='/help'),
            dict(name='通知公告', icon='icon-info', link='/announce'),
            dict(name='相关工具', icon='icon-tool', sub_items=[
                dict(name='自动标点', icon='icon-subitem', link='/com/punctuate'),
                dict(name='全文检索', icon='icon-subitem', link='/com/search'),
            ]),
        ]

        # nlc左侧菜单项
        nlc_items = [
            dict(name='首页', icon='icon-home', link='/home'),
            dict(name='古籍库', icon='icon-tripitaka', link='/tripitaka/list'),
            dict(name='任务大厅', icon='icon-task-lobby', sub_items=[
                dict(name='切分校对', icon='icon-subitem', link='/task/lobby/cut_proof'),
                dict(name='切分审定', icon='icon-subitem', link='/task/lobby/cut_review'),
                dict(name='文字校对', icon='icon-subitem', link='/task/lobby/text_proof'),
                dict(name='文字审定', icon='icon-subitem', link='/task/lobby/text_review'),
            ]),
            dict(name='我的任务', icon='icon-task-my', sub_items=[
                dict(name='切分校对', icon='icon-subitem', link='/task/my/cut_proof'),
                dict(name='切分审定', icon='icon-subitem', link='/task/my/cut_review'),
                dict(name='文字校对', icon='icon-subitem', link='/task/my/text_proof'),
                dict(name='文字审定', icon='icon-subitem', link='/task/my/text_review'),
            ]),
            dict(name='任务管理', icon='icon-task-admin', link='/page/task/list'),
            dict(name='数据管理', icon='icon-data', sub_items=[
                dict(name='导图片', icon='icon-subitem', link='/data/image'),
                dict(name='部数据', icon='icon-subitem', link='/data/tripitaka'),
                dict(name='册数据', icon='icon-subitem', link='/data/volume'),
                dict(name='页数据', icon='icon-subitem', link='/page/list'),
                dict(name='异体字', icon='icon-subitem', link='/data/variant'),
            ]),
            dict(name='人员管理', icon='icon-users', sub_items=[
                dict(name='用户管理', icon='icon-subitem', link='/user/admin'),
                dict(name='授权管理', icon='icon-subitem', link='/user/roles'),
            ]),
            dict(name='系统管理', icon='icon-admin', sub_items=[
                dict(name='脚本管理', icon='icon-subitem', link='/sys/script'),
                dict(name='脚本日志', icon='icon-subitem', link='/sys/oplog'),
                dict(name='操作日志', icon='icon-subitem', link='/sys/log'),
            ]),
            dict(name='相关工具', icon='icon-tool', sub_items=[
                dict(name='自动标点', icon='icon-subitem', link='/com/punctuate'),
            ]),
            dict(name='帮助中心', icon='icon-help', link='/help'),
            dict(name='通知公告', icon='icon-info', link='/announce'),
        ]

        # 计算当前用户有权访问的菜单
        skin = h.prop(self.handler.config, 'site.skin')
        items = nlc_items if skin == 'nlc' else base_items
        display_items = []
        for item in items:
            if not is_enabled(item.get('name')):
                continue
            if item.get('link') and self.handler.can_access(item['link']):
                item['id'] = re.sub('[/_]', '-', item['link'][1:])
                display_items.append(item)
            if item.get('sub_items'):
                sub_items = []
                for sub in item['sub_items']:
                    if is_enabled(sub.get('name')) and sub.get('link') and self.handler.can_access(sub['link']):
                        sub['id'] = re.sub('[/_]', '-', sub['link'][1:])
                        sub_items.append(sub)
                if sub_items:
                    item['sub_items'] = sub_items
                    display_items.append(item)
        return self.render_string('com/_left.html', display_items=display_items, active_id=active_id)


class ComHead(UIModule):
    def render(self):
        return self.render_string('com/_head.html')


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

        return self.render_string('com/_pager.html', get_page_uri=self.get_page_uri, **pager)


class ComTable(UIModule):

    def render(self, docs, table_fields, actions, info_fields=None, hide_fields=None, order='',
               pack=None, format_value=None):
        pack = dumps if not pack else pack
        hide_fields = [] if hide_fields is None else hide_fields
        format_value = h.format_value if not format_value else format_value
        info_fields = [d['id'] for d in table_fields] if info_fields is None else info_fields
        return self.render_string(
            'com/_table.html', docs=docs, order=order, actions=actions, table_fields=table_fields,
            info_fields=info_fields, hide_fields=hide_fields, format_value=format_value,
            pack=pack, prop=h.prop
        )


class ComModal(UIModule):
    def render(self, modal_fields, id='', title='', buttons=None):
        buttons = [('modal-cancel', '取消'), ('modal-confirm', '确定')] if buttons is None else buttons
        return self.render_string('com/_modal.html', modal_fields=modal_fields, id=id, title=title, buttons=buttons)


class ReturnModal(UIModule):
    def render(self):
        buttons = [('modal-cancel', '取消'), ('modal-confirm', '退回后返回大厅'), ('modal-next', '退回后领下一条')]
        modal_fields = [
            {'id': 'return_reason', 'name': '退回理由', 'input_type': 'textarea'},
            {'id': 'options', 'name': '　', 'input_type': 'radio', 'options': [
                '空白页', '图片页', '体例未规定', '字体太草', '字图歪斜', '操作无权限', '大片字迹模糊', '大量字框切错', '大量特殊符号'
            ]},
        ]
        return self.render_string('com/_modal.html', modal_fields=modal_fields, id='returnModal', title='退回任务',
                                  buttons=buttons)


class DoubtModal(UIModule):
    def render(self):
        buttons = [('modal-cancel', '取消'), ('modal-confirm', '确定')]
        modal_fields = [
            {'id': 'doubt_input', 'name': '存疑文本'},
            {'id': 'doubt_reason', 'name': '存疑理由', 'input_type': 'textarea'}
        ]
        return self.render_string('com/_modal.html', modal_fields=modal_fields, id='doubtModal', title='存疑',
                                  buttons=buttons)


class TaskRemarkModal(UIModule):
    def render(self):
        buttons = [('modal-cancel', '取消'), ('modal-confirm', '确定')]
        modal_fields = [
            {'id': 'is_sample', 'name': '示例任务', 'input_type': 'radio', 'options': ['是', '否']},
            {'id': 'remark', 'name': '备注内容'},
            {'id': 'options', 'name': '　', 'input_type': 'radio', 'options': ['没问题', '还可以', '不合要求']},
        ]
        return self.render_string('com/_modal.html', modal_fields=modal_fields, id='remarkModal', title='备注',
                                  buttons=buttons)


class PageRemarkModal(UIModule):
    def render(self):
        buttons = [('modal-cancel', '取消'), ('modal-confirm', '确定')]
        modal_fields = [
            {'id': 'fields', 'name': '备注字段', 'input_type': 'radio', 'options': ['切分', '文本']},
            {'id': 'remark', 'name': '备注内容'},
            {'id': 'options', 'name': '　', 'input_type': 'radio', 'options': ['没问题', '还可以', '不合要求']},
        ]
        return self.render_string('com/_modal.html', modal_fields=modal_fields, id='remarkModal', title='备注',
                                  buttons=buttons)


class PageConfigModal(UIModule):
    def render(self):
        buttons = [('modal-cancel', '取消'), ('modal-confirm', '确定')]
        modal_fields = [
            {'id': 'may_wrong', 'name': '易错字列表', 'input_type': 'textarea'},
            {'id': 'img_opacity', 'name': '图片透明度'}
        ]
        return self.render_string('com/_modal.html', modal_fields=modal_fields, id='pageConfigModal', title='配置',
                                  buttons=buttons)


class TaskConfigModal(UIModule):
    def render(self, config_fields=None):
        title = '配置项'
        buttons = [('modal-cancel', '取消'), ('modal-confirm', '确定')]
        fields = [{'id': 'auto-pick', 'name': '提交后自动领新任务', 'input_type': 'radio', 'options': ['是', '否']}]
        return self.render_string('com/_config.html', modal_fields=config_fields or fields, id='taskConfigModal',
                                  title=title, buttons=buttons)


class TxtDiff(UIModule):
    def render(self, cmp_data):
        """文字校对的文字区"""
        return self.render_string(
            'com/_txt_diff.html', blocks=cmp_data,
            sort_by_key=lambda d: sorted(d.items(), key=lambda t: t[0])
        )


class PageTxt(UIModule):

    def render(self, txts, active=None, cmp_data=None):
        """ 页文本显示
        :param txts, 格式为[(txt, field, label), (txt, field, label)...]
        :param active, txts文本中，当前显示哪个文本
        :param cmp_data, 比对文本。如果比对文本不为空，则优先显示比对文本
        """
        active = None if cmp_data else active if active else txts[0][1] if txts else None
        return self.render_string('com/_page_txt.html', txts=txts, cmp_data=cmp_data, active=active,
                                  txt2html=Ph.txt2html)
