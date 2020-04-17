#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from bson import json_util
from tornado.web import UIModule
from tornado.escape import to_basestring
from .page import Page
from .base import PageHandler
from controller import errors as e
from controller.task.task import Task


class PageAdminHandler(PageHandler):
    URL = '/page/admin'

    page_title = '页数据管理'
    table_fields = [
        {'id': 'name', 'name': '页编码'},
        {'id': 'source', 'name': '分类'},
        {'id': 'layout', 'name': '页面结构'},
        {'id': 'img_cloud_path', 'name': '云图路径'},
        {'id': 'uni_sutra_code', 'name': '统一经编码'},
        {'id': 'sutra_code', 'name': '经编码'},
        {'id': 'reel_code', 'name': '卷编码'},
        {'id': 'tasks', 'name': '任务'},
        {'id': 'box_ready', 'name': '切分就绪'},
        {'id': 'remark_box', 'name': '切分备注'},
        {'id': 'remark_text', 'name': '文字备注'},
    ]
    info_fields = [
        'name', 'source', 'box_ready', 'layout', 'remark_box', 'remark_text'
    ]
    hide_fields = [
        'uni_sutra_code', 'sutra_code', 'reel_code', 'box_ready',
    ]
    operations = [
        {'operation': 'bat-remove', 'label': '批量删除', 'url': '/api/page/delete'},
        {'operation': 'btn-duplicate', 'label': '查找重复'},
        {'operation': 'bat-source', 'label': '更新分类'},
        {'operation': 'bat-export-char', 'label': '生成字表'},
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
        {'operation': 'btn-publish', 'label': '发布任务', 'groups': [
            {'operation': k, 'label': v} for k, v in PageHandler.task_types.items()
        ]},
    ]
    actions = [
        {'action': 'btn-nav', 'label': '浏览'},
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-box', 'label': '字框'},
        {'action': 'btn-order', 'label': '字序'},
        {'action': 'btn-cmp-txt', 'label': '比对文本'},
        {'action': 'btn-update', 'label': '更新'},
        {'action': 'btn-remove', 'label': '删除', 'url': '/api/page/delete'},
    ]
    update_fields = [
        {'id': 'name', 'name': '页编码', 'readonly': True},
        {'id': 'source', 'name': '分　类'},
        {'id': 'box_ready', 'name': '切分就绪', 'input_type': 'radio', 'options': ['是', '否']},
        {'id': 'layout', 'name': '图片结构', 'input_type': 'radio', 'options': Page.layouts},
        {'id': 'remark_box', 'name': '切分备注'},
        {'id': 'remark_text', 'name': '文本备注'},
    ]
    task_statuses = {
        '': '', 'un_published': '未发布', 'published': '已发布未领取', 'pending': '等待前置任务',
        'picked': '进行中', 'returned': '已退回', 'finished': '已完成',
    }

    def get_duplicate_condition(self):
        pages = list(self.db.page.aggregate([
            {'$group': {'_id': '$name', 'count': {'$sum': 1}}},
            {'$match': {'count': {'$gte': 2}}},
        ]))
        condition = {'name': {'$in': [p['_id'] for p in pages]}}
        params = {'duplicate': 'true'}
        return condition, params

    def get(self):
        """ 页数据管理"""
        try:
            kwargs = self.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']

            if self.get_query_argument('duplicate', '') == 'true':
                condition, params = self.get_duplicate_condition()
            else:
                condition, params = Page.get_page_search_condition(self.request.query)
            fields = ['chars', 'columns', 'blocks', 'ocr', 'ocr_col', 'text', 'txt_html']
            docs, pager, q, order = Page.find_by_page(self, condition, None, 'page_code', {f: 0 for f in fields})
            self.render('page_admin.html', docs=docs, pager=pager, q=q, order=order, params=params,
                        task_statuses=self.task_statuses, format_value=self.format_value,
                        Task=Task, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class PageBrowseHandler(PageHandler):
    URL = '/page/browse/@page_name'

    def get(self, page_name):
        """ 浏览页面数据"""
        edit_fields = [
            {'id': 'name', 'name': '页编码', 'readonly': True},
            {'id': 'source', 'name': '分　类'},
            {'id': 'layout', 'name': '图片结构', 'input_type': 'radio', 'options': self.layouts},
            {'id': 'box_ready', 'name': '切分就绪', 'input_type': 'radio', 'options': ['是', '否']},
        ]

        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            condition = self.get_page_search_condition(self.request.query)[0]
            to = self.get_query_argument('to', '')
            if to == 'next':
                condition['page_code'] = {'$gt': page['page_code']}
                page = self.db.page.find_one(condition, sort=[('page_code', 1)])
            elif to == 'prev':
                condition['page_code'] = {'$lt': page['page_code']}
                page = self.db.page.find_one(condition, sort=[('page_code', -1)])
            if not page:
                message = '没有找到页面%s的%s' % (page_name, '上一页' if to == 'prev' else '下一页')
                return self.send_error_response(e.no_object, message=message)

            txts = self.get_txts(page)
            img_url = self.get_web_img(page['name'])
            chars_col = self.get_chars_col(page['chars'])
            info = {f['id']: self.prop(page, f['id'], '') for f in edit_fields}
            btn_config = json_util.loads(self.get_secure_cookie('page_browse_button') or '{}')
            self.render('page_browse.html', page=page, img_url=img_url, chars_col=chars_col, txts=txts,
                        info=info, btn_config=btn_config, edit_fields=edit_fields)

        except Exception as error:
            return self.send_db_error(error)


class PageViewHandler(PageHandler):
    URL = '/page/@page_name'

    def get(self, page_name):
        """ 查看Page页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)

            self.pack_boxes(page)
            txts = self.get_txts(page)
            img_url = self.get_web_img(page['name'])
            chars_col = self.get_chars_col(page['chars'])
            txt_off = self.get_query_argument('txt', None) == 'off'
            cid = self.get_query_argument('char_name', '').split('_')[-1]
            self.render('page_view.html', page=page, img_url=img_url, chars_col=chars_col, txts=txts,
                        txt_off=txt_off, cur_cid=cid)

        except Exception as error:
            return self.send_db_error(error)


class PageInfoHandler(PageHandler):
    URL = '/page/info/@page_name'

    def get(self, page_name):
        """ 页面详情"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)

            fields1 = ['txt', 'ocr', 'ocr_col', 'cmp']
            page_txt = {k: self.get_txt(page, k) for k in fields1 if self.get_txt(page, k)}
            fields2 = ['blocks', 'columns', 'chars', 'chars_col']
            page_box = {k: self.prop(page, k) for k in fields2 if self.prop(page, k)}
            fields3 = list(set(page.keys()) - set(fields1 + fields2))
            metadata = {k: self.prop(page, k) for k in fields3 if self.prop(page, k)}
            page_tasks = self.prop(page, 'tasks') or {}

            self.render('page_info.html', page=page, metadata=metadata, page_txt=page_txt, page_box=page_box,
                        page_tasks=page_tasks, Page=Page, Task=Task)

        except Exception as error:
            return self.send_db_error(error)


class PageBoxHandler(PageHandler):
    URL = ['/page/box/@page_name',
           '/page/box/edit/@page_name']

    def get(self, page_name):
        """ 切分校对页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            self.pack_boxes(page)
            self.check_box_access(page, 'raw')
            readonly = '/edit' not in self.request.path
            img_url = self.get_web_img(page['name'], 'page')
            self.render('page_box.html', page=page, img_url=img_url, readonly=readonly)

        except Exception as error:
            return self.send_db_error(error)


class PageOrderHandler(PageHandler):
    URL = ['/page/order/@page_name',
           '/page/order/edit/@page_name']

    def get(self, page_name):
        """ 字序校对页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            self.pack_boxes(page)
            readonly = '/edit' not in self.request.path
            img_url = self.get_web_img(page['name'], 'page')
            reorder = self.get_query_argument('reorder', '')
            if reorder:
                page['chars'] = self.reorder_boxes(page=page, direction=reorder)[2]
            chars_col = self.get_chars_col(page['chars'])
            self.render('page_order.html', page=page, chars_col=chars_col, img_url=img_url, readonly=readonly)

        except Exception as error:
            return self.send_db_error(error)


class PageCmpTxtHandler(PageHandler):
    URL = ['/page/cmp_txt/@page_name',
           '/page/cmp_txt/edit/@page_name']

    def get(self, page_name):
        """ 比对文本页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            self.pack_boxes(page)
            ocr = self.get_txt(page, 'ocr')
            cmp = self.get_txt(page, 'cmp')
            readonly = '/edit' not in self.request.path
            img_url = self.get_web_img(page['name'], 'page')
            self.render('page_cmp_txt.html', page=page, ocr=ocr, cmp=cmp, img_url=img_url, readonly=readonly)

        except Exception as error:
            return self.send_db_error(error)


class PageTxtHandler(PageHandler):
    URL = ['/page/txt/@page_name',
           '/page/txt/edit/@page_name']

    def get(self, page_name):
        """ 单字修改页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='页面%s不存在' % page_name)

            self.pack_boxes(page)
            chars = page['chars']
            chars_col = self.get_chars_col(chars)
            char_dict = {c['cid']: c for c in chars}
            img_url = self.get_web_img(page['name'])
            readonly = '/edit' not in self.request.path
            txt_types = {'': '没问题', 'M': '模糊或残损', 'N': '不确定', '*': '不认识'}
            self.render('page_char.html', page=page, chars=chars, chars_col=chars_col, char_dict=char_dict,
                        txt_types=txt_types, img_url=img_url, readonly=readonly)

        except Exception as error:
            return self.send_db_error(error)


class PageTextHandler(PageHandler):
    URL = ['/page/txt/@page_name',
           '/page/txt/edit/@page_name']

    def get(self, page_name):
        """ 文字校对页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            txts = [(self.get_txt(page, f), f, Page.get_field_name(f)) for f in ['txt', 'ocr', 'ocr_col', 'cmp']]
            txts = [t for t in txts if t[0]]
            txt_dict = {t[1]: t for t in txts}
            cmp_data = self.prop(page, 'txt_html')
            txt_fields = self.prop(page, 'txt_fields')
            doubts = [(self.prop(page, 'txt_doubt', ''), '校对存疑')]
            if not cmp_data:
                txt_fields = [t[1] for t in txts]
                cmp_data = self.diff(*[t[0] for t in txts])
                cmp_data = to_basestring(TextArea(self).render(cmp_data))
            readonly = '/edit' not in self.request.path
            img_url = self.get_web_img(page['name'], 'page')
            return self.render('page_txt.html', page=page, img_url=img_url, txts=txts, txt_dict=txt_dict,
                               txt_fields=txt_fields, cmp_data=cmp_data,
                               doubts=doubts, readonly=readonly)

        except Exception as error:
            return self.send_db_error(error)


class TextArea(UIModule):
    """ 文字校对的文字区"""

    def render(self, cmp_data):
        return self.render_string('page_text_area.html', blocks=cmp_data,
                                  sort_by_key=lambda d: sorted(d.items(), key=lambda t: t[0]))


class PageTaskAdminHandler(PageHandler):
    URL = '/page/task/admin'

    page_title = '页任务管理'
    search_tips = '请搜索页编码、批次号或备注'
    search_fields = ['doc_id', 'batch', 'remark']
    operations = [
        {'operation': 'bat-remove', 'label': '批量删除', 'title': '/task/delete'},
        {'operation': 'bat-assign', 'label': '批量指派', 'data-target': 'assignModal'},
        {'operation': 'bat-batch', 'label': '更新批次'},
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
        {'operation': 'btn-statistic', 'label': '结果统计', 'groups': [
            {'operation': 'picked_user_id', 'label': '按用户'},
            {'operation': 'task_type', 'label': '按类型'},
            {'operation': 'status', 'label': '按状态'},
        ]},
    ]
    actions = [
        {'action': 'btn-nav', 'label': '浏览'},
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-history', 'label': '历程'},
        {'action': 'btn-delete', 'label': '删除'},
        {'action': 'btn-republish', 'label': '重新发布', 'disabled': lambda d: d['status'] not in ['picked', 'failed']},
    ]
    hide_fields = ['_id', 'return_reason', 'create_time', 'updated_time', 'publish_by']
    update_fields = []

    def get(self):
        """ 任务管理-页任务管理"""
        try:
            # 模板参数
            kwargs = self.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            kwargs['table_fields'] = [
                {'id': '_id', 'name': '主键'},
                {'id': 'doc_id', 'name': '页编码'},
                {'id': 'batch', 'name': '批次号'},
                {'id': 'task_type', 'name': '类型', 'filter': self.task_types},
                {'id': 'status', 'name': '状态', 'filter': self.task_statuses},
                {'id': 'priority', 'name': '优先级', 'filter': self.priorities},
                {'id': 'steps', 'name': '步骤'},
                {'id': 'pre_tasks', 'name': '前置任务'},
                {'id': 'return_reason', 'name': '退回理由'},
                {'id': 'create_time', 'name': '创建时间'},
                {'id': 'updated_time', 'name': '更新时间'},
                {'id': 'publish_time', 'name': '发布时间'},
                {'id': 'publish_by', 'name': '发布人'},
                {'id': 'picked_time', 'name': '领取时间'},
                {'id': 'picked_by', 'name': '领取人'},
                {'id': 'finished_time', 'name': '完成时间'},
                {'id': 'remark', 'name': '备注'},
            ]
            condition, params = self.get_task_search_condition(self.request.query, 'page')
            p = {f: 0 for f in ['input', 'result']}
            docs, pager, q, order = self.find_by_page(self, condition, self.search_fields, '-_id', p)
            self.render(
                'task_admin_page.html', docs=docs, pager=pager, order=order, q=q, params=params,
                format_value=self.format_value, **kwargs,
            )
        except Exception as error:
            return self.send_db_error(error)


class PageTaskStatHandler(PageHandler):
    URL = '/page/task/statistic'

    def get(self, collection):
        """ 根据用户、任务类型或任务状态统计页任务"""
        try:
            kind = self.get_query_argument('kind', '')
            if kind not in ['picked_user_id', 'task_type', 'status']:
                return self.send_error_response(e.statistic_type_error, message='只能按用户、任务类型或任务状态统计')

            condition = self.get_task_search_condition(self.request.query, collection)[0]
            counts = list(self.db.task.aggregate([
                {'$match': condition},
                {'$group': {'_id': '$%s' % kind, 'count': {'$sum': 1}}},
            ]))

            trans = {}
            if kind == 'picked_user_id':
                users = list(self.db.user.find({'_id': {'$in': [c['_id'] for c in counts]}}))
                trans = {u['_id']: u['name'] for u in users}
            elif kind == 'task_type':
                trans = self.task_names()
            elif kind == 'status':
                trans = self.task_statuses
            label = dict(picked_user_id='用户', task_type='任务类型', status='任务状态')[kind]

            self.render('task_statistic.html', counts=counts, kind=kind, label=label, trans=trans)

        except Exception as error:
            return self.send_db_error(error)


class PageTaskResumeHandler(PageHandler):
    URL = '/page/task/resume/@page_name'

    order = [
        'upload_cloud', 'ocr_box', 'cut_proof', 'cut_review', 'ocr_text', 'text_proof_1',
        'text_proof_2', 'text_proof_3', 'text_review', 'text_hard'
    ]
    display_fields = [
        'doc_id', 'task_type', 'status', 'pre_tasks', 'steps', 'priority',
        'updated_time', 'finished_time', 'publish_by', 'publish_time',
        'picked_by', 'picked_time', 'message'
    ]

    def get(self, page_name):
        """ 页任务简历"""
        from functools import cmp_to_key
        try:
            page = self.db.page.find_one({'name': page_name}) or dict(name=page_name)
            tasks = list(self.db.task.find({'collection': 'page', 'doc_id': page_name}))
            tasks.sort(key=cmp_to_key(lambda a, b: self.order.index(a['task_type']) - self.order.index(b['task_type'])))
            self.render('task_resume.html', page=page, tasks=tasks, display_fields=self.display_fields)

        except Exception as error:
            return self.send_db_error(error)


class PageTaskLobbyHandler(PageHandler):
    URL = '/task/lobby/@page_task'

    def get(self, task_type):
        """ 任务大厅"""

        try:
            q = self.get_query_argument('q', '')
            tasks, total_count = self.find_lobby(task_type, q=q)
            collection = self.get_data_collection(task_type)
            fields = [('doc_id', '页编码'), ('priority', '优先级')] if collection == 'page' else [
                ('txt_kind', '字种'), ('char_count', '单字数量')]
            self.render('task_lobby.html', tasks=tasks, task_type=task_type, total_count=total_count,
                        fields=fields, format_value=self.format_value)
        except Exception as error:
            return self.send_db_error(error)


class PageTaskMyHandler(PageHandler):
    URL = '/task/my/@page_task'

    search_tips = '请搜索页编码'
    search_fields = ['doc_id']
    operations = []
    img_operations = []
    actions = [
        {'action': 'my-task-view', 'label': '查看'},
        {'action': 'my-task-do', 'label': '继续', 'disabled': lambda d: d['status'] == 'finished'},
        {'action': 'my-task-update', 'label': '更新', 'disabled': lambda d: d['status'] == 'picked'},
    ]
    table_fields = [
        {'id': 'doc_id', 'name': '页编码'},
        {'id': 'task_type', 'name': '类型'},
        {'id': 'status', 'name': '状态'},
        {'id': 'picked_time', 'name': '领取时间'},
        {'id': 'finished_time', 'name': '完成时间'},
    ]
    hide_fields = ['task_type']
    info_fields = ['doc_id', 'task_type', 'status', 'picked_time', 'finished_time']
    update_fields = []

    def get(self, task_type):
        """ 我的任务"""
        try:
            condition = {
                'task_type': {'$regex': task_type} if self.is_group(task_type) else task_type,
                'status': {'$in': [self.STATUS_PICKED, self.STATUS_FINISHED]},
                'picked_user_id': self.user_id
            }
            docs, pager, q, order = self.find_by_page(self, condition, default_order='-picked_time')
            kwargs = self.get_template_kwargs()
            self.render('task_my.html', docs=docs, pager=pager, q=q, order=order,
                        format_value=self.format_value, **kwargs)

        except Exception as error:
            return self.send_db_error(error)
