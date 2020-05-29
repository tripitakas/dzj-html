#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from bson import json_util
from .page import Page
from .base import PageHandler
from controller import errors as e
from controller import helper as h
from controller.task.task import Task


class PageListHandler(PageHandler):
    URL = '/page/list'

    page_title = '页数据管理'
    table_fields = [
        {'id': 'name', 'name': '页编码'},
        {'id': 'source', 'name': '分类'},
        {'id': 'layout', 'name': '页面结构'},
        {'id': 'uni_sutra_code', 'name': '统一经编码'},
        {'id': 'sutra_code', 'name': '经编码'},
        {'id': 'reel_code', 'name': '卷编码'},
        {'id': 'tasks', 'name': '任务'},
        {'id': 'box_ready', 'name': '切分就绪'},
        {'id': 'remark_box', 'name': '切分备注'},
        {'id': 'remark_text', 'name': '文本备注'},
        {'id': 'op_text', 'name': '文本匹配'},
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
        {'operation': 'bat-gen-chars', 'label': '生成字表'},
        {'operation': 'btn-check-match', 'label': '检查图文匹配'},
        {'operation': 'btn-fetch-cmp', 'label': '获取比对文本'},
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
        {'operation': 'btn-publish', 'label': '发布任务', 'groups': [
            {'operation': k, 'label': name} for k, name in PageHandler.task_names('page', True).items()
        ]},
    ]
    actions = [
        {'action': 'btn-box', 'label': '字框'},
        {'action': 'btn-order', 'label': '字序'},
        {'action': 'btn-nav', 'label': '浏览'},
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-update', 'label': '更新'},
        {'action': 'btn-remove', 'label': '删除', 'url': '/api/page/delete'},
    ]
    update_fields = [
        {'id': 'name', 'name': '页编码', 'readonly': True},
        {'id': 'source', 'name': '分　类'},
        {'id': 'box_ready', 'name': '切分就绪', 'input_type': 'radio', 'options': ['是', '否']},
        {'id': 'layout', 'name': '图片结构', 'input_type': 'radio', 'options': PageHandler.layouts},
        {'id': 'remark_box', 'name': '切分备注'},
        {'id': 'remark_text', 'name': '文本备注'},
    ]
    task_statuses = {
        '': '', 'un_published': '未发布', 'published': '已发布未领取', 'pending': '等待前置任务',
        'picked': '进行中', 'returned': '已退回', 'finished': '已完成',
    }
    match_fields = {'cmp_txt': '比对文本', 'ocr_col': 'OCR列文', 'txt': '校对文本'}
    match_statuses = {'': '', None: '无', True: '匹配', False: '不匹配'}

    def format_value(self, value, key=None, doc=None):
        """ 格式化page表的字段输出"""

        def format_txt(field, show_none=True):
            txt = self.get_txt(doc, field)
            if txt:
                return '<a title="%s">%s%s</a>' % (
                    field, self.match_fields.get(field), t.get(self.prop(doc, 'txt_match.%s.status' % field)) or ''
                )
            elif show_none:
                return '<a title="%s">%s%s(无)</a>' % (
                    field, self.match_fields.get(field), t.get(self.prop(doc, 'txt_match.%s.status' % field)) or '',
                )
            else:
                return ''

        if key == 'tasks' and value:
            return '<br/>'.join([
                '%s/%s' % (self.get_task_name(t), self.get_status_name(status))
                for t, status in value.items()
            ])
        if key == 'op_text':
            t = {True: '√', False: '×'}
            return '<br/>'.join([format_txt(k, k != 'txt') for k in ['ocr_col', 'cmp_txt', 'txt']])
        return h.format_value(value, key, doc)

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
            # fields = ['chars', 'columns', 'blocks', 'cmp_txt', 'ocr', 'ocr_col', 'txt']
            docs, pager, q, order = Page.find_by_page(self, condition, None, 'page_code', None)
            self.render('page_list.html', docs=docs, pager=pager, q=q, order=order, params=params,
                        task_statuses=self.task_statuses, match_statuses=self.match_statuses,
                        format_value=self.format_value, **kwargs)

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
            cid = self.get_query_argument('cid', '')
            img_url = self.get_web_img(page['name'])
            chars_col = self.get_chars_col(page['chars'])
            txt_off = self.get_query_argument('txt', None) == 'off'
            txt_dict = {t[1]: t for t in txts}
            self.render('page_view.html', page=page, img_url=img_url, chars_col=chars_col, txts=txts,
                        txt_off=txt_off, txt_dict=txt_dict, cur_cid=cid)

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

            page_tasks = self.prop(page, 'tasks') or []
            fields1 = ['txt', 'ocr', 'ocr_col', 'cmp']
            page_txts = {k: self.get_txt(page, k) for k in fields1 if self.get_txt(page, k)}
            fields2 = ['blocks', 'columns', 'chars', 'chars_col']
            page_boxes = {k: self.prop(page, k) for k in fields2 if self.prop(page, k)}
            fields3 = list(set(page.keys()) - set(fields1 + fields2) - {'tasks'})
            metadata = {k: self.prop(page, k) for k in fields3 if self.prop(page, k)}

            self.render('page_info.html', page=page, metadata=metadata, page_txts=page_txts, page_boxes=page_boxes,
                        page_tasks=page_tasks, Page=Page, Task=Task)

        except Exception as error:
            return self.send_db_error(error)


class PageBoxHandler(PageHandler):
    URL = '/page/box/@page_name'

    def get(self, page_name):
        """ 切分校对页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            self.pack_boxes(page)
            self.set_box_access(page)
            img_url = self.get_web_img(page['name'], 'page')
            self.render('page_box.html', page=page, img_url=img_url, readonly=False)

        except Exception as error:
            return self.send_db_error(error)


class PageOrderHandler(PageHandler):
    URL = '/page/order/@page_name'

    def get(self, page_name):
        """ 字序校对页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            self.pack_boxes(page)
            img_url = self.get_web_img(page['name'], 'page')
            reorder = self.get_query_argument('reorder', '')
            if reorder:
                page['chars'] = self.reorder_boxes(page=page, direction=reorder)[2]
            chars_col = self.get_chars_col(page['chars'])
            self.render('page_order.html', page=page, chars_col=chars_col, img_url=img_url, readonly=False)

        except Exception as error:
            return self.send_db_error(error)


class PageTaskCutHandler(PageHandler):
    URL = ['/task/(cut_proof|cut_review)/@task_id',
           '/task/do/(cut_proof|cut_review)/@task_id',
           '/task/browse/(cut_proof|cut_review)/@task_id',
           '/task/update/(cut_proof|cut_review)/@task_id']

    def get(self, task_type, task_id):
        """ 切分校对、审定页面"""
        page = self.db.page.find_one({'name': self.task['doc_id']})
        if not page:
            self.send_error_response(e.no_object, message='没有找到页面%s' % self.task['doc_id'])
        self.pack_boxes(page)
        img_url = self.get_web_img(page['name'], 'page')
        if self.steps['current'] == 'order':
            reorder = self.get_query_argument('reorder', '')
            if reorder:
                page['chars'] = self.reorder_boxes(page=page, direction=reorder)[2]
            chars_col = self.get_chars_col(page['chars'])
            self.render('page_order.html', page=page, chars_col=chars_col, img_url=img_url, readonly=self.readonly)
        else:
            self.set_box_access(page, task_type)
            self.render('page_box.html', page=page, img_url=img_url, readonly=self.readonly)


class PageTxtMatchHandler(PageHandler):
    URL = '/page/(ocr_col|cmp_txt|txt)/@page_name'

    def get(self, field, page_name):
        """ 文字匹配页面"""
        self.txt_match(self, field, page_name)

    @staticmethod
    def txt_match(self, field, page_name):
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            cmp_txt = self.get_txt(page, field)
            field_name = Page.get_field_name(field)
            if not cmp_txt:
                if field == 'cmp_txt':
                    self.redirect('/page/find_cmp/' + page_name)
                else:
                    self.send_error_response(e.no_object, message='页面没有%s' % field_name)

            self.pack_boxes(page)
            char_txt = self.get_txt(page, 'ocr')
            cmp_data = self.match_diff(char_txt, cmp_txt)
            img_url = self.get_web_img(page['name'], 'page')
            txt_match = self.prop(page, 'txt_match.' + field)
            self.render('page_txt_match.html', page=page, img_url=img_url, char_txt=char_txt, cmp_data=cmp_data,
                        field=field, field_name=field_name, txt_match=txt_match)

        except Exception as error:
            return self.send_db_error(error)


class PageTaskTxtMatchHandler(PageHandler):
    URL = ['/task/txt_match/@task_id',
           '/task/do/txt_match/@task_id',
           '/task/browse/txt_match/@task_id',
           '/task/update/txt_match/@task_id']

    def get(self, task_id):
        """ 图文匹配页面"""
        page_name, field = self.task['doc_id'], self.prop(self.task, 'params.field')
        PageTxtMatchHandler.txt_match(self, field, page_name)


class PageFindCmpHandler(PageHandler):
    URL = '/page/find_cmp/@page_name'

    def get(self, page_name):
        """ 寻找比对文本页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            self.pack_boxes(page)
            img_url = self.get_web_img(page['name'], 'page')
            self.render('page_find_cmp.html', page=page, img_url=img_url, readonly=True, ocr=self.get_txt(page, 'ocr'),
                        cmp_txt=self.get_txt(page, 'cmp_txt'), )

        except Exception as error:
            return self.send_db_error(error)


class PageTaskListHandler(PageHandler):
    URL = '/page/task/list'

    page_title = '页任务管理'
    search_tips = '请搜索页编码、批次号或备注'
    search_fields = ['doc_id', 'batch', 'remark']
    table_fields = [
        {'id': '_id', 'name': '主键'},
        {'id': 'doc_id', 'name': '页编码'},
        {'id': 'batch', 'name': '批次号'},
        {'id': 'task_type', 'name': '类型', 'filter': PageHandler.task_names('page')},
        {'id': 'num', 'name': '校次'},
        {'id': 'status', 'name': '状态', 'filter': PageHandler.task_statuses},
        {'id': 'priority', 'name': '优先级', 'filter': PageHandler.priorities},
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
    operations = [
        {'operation': 'bat-remove', 'label': '批量删除', 'url': '/task/delete'},
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
            kwargs = self.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            condition, params = self.get_task_search_condition(self.request.query, 'page')
            docs, pager, q, order = self.find_by_page(self, condition, self.search_fields, '-_id',
                                                      {'input': 0, 'result': 0})
            self.render('page_task_list.html', docs=docs, pager=pager, order=order, q=q, params=params,
                        format_value=self.format_value,
                        **kwargs)
        except Exception as error:
            return self.send_db_error(error)


class PageTaskStatHandler(PageHandler):
    URL = '/page/task/statistic'

    def get(self):
        """ 根据用户、任务类型或任务状态统计页任务"""
        try:
            kind = self.get_query_argument('kind', '')
            if kind not in ['picked_user_id', 'task_type', 'status']:
                return self.send_error_response(e.statistic_type_error, message='只能按用户、任务类型或任务状态统计')

            counts = list(self.db.task.aggregate([
                {'$match': self.get_task_search_condition(self.request.query, 'page')[0]},
                {'$group': {'_id': '$%s' % kind, 'count': {'$sum': 1}}},
            ]))

            trans = {}
            if kind == 'picked_user_id':
                users = list(self.db.user.find({'_id': {'$in': [c['_id'] for c in counts]}}))
                trans = {u['_id']: u['name'] for u in users}
            elif kind == 'task_type':
                trans = {k: t['name'] for k, t in PageHandler.task_types.items()}
            elif kind == 'status':
                trans = self.task_statuses
            label = dict(picked_user_id='用户', task_type='任务类型', status='任务状态')[kind]
            self.render('task_statistic.html', counts=counts, kind=kind, label=label, trans=trans, collection='page')

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
