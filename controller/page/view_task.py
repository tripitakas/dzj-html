#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from bson import json_util
from controller import errors as e
from controller.page.base import PageHandler
from controller.page.view import PageTxtHandler


class PageTaskListHandler(PageHandler):
    URL = '/page/task/list'

    page_title = '页任务管理'
    search_tips = '请搜索页编码、批次号或备注'
    search_fields = ['doc_id', 'batch', 'remark']
    table_fields = [
        {'id': '_id', 'name': '主键'},
        {'id': 'doc_id', 'name': '页编码'},
        {'id': 'char_count', 'name': '单字数量'},
        {'id': 'batch', 'name': '批次号'},
        {'id': 'task_type', 'name': '类型', 'filter': PageHandler.task_names('page', True, True)},
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

    def get_template_kwargs(self, fields=None):
        kwargs = super().get_template_kwargs()
        readonly = '任务管理员' not in self.current_user['roles']
        if readonly:
            kwargs['actions'] = [{'action': 'btn-nav', 'label': '浏览'}]
            kwargs['operations'] = [{'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'}]
        return kwargs

    def get_task_search_condition(self, request_query, collection=None):
        condition, params = super().get_task_search_condition(request_query, collection)
        readonly = '任务管理员' not in self.current_user['roles']
        if readonly:
            condition['task_type'] = {'$in': ['cut_proof', 'cut_review']}
        return condition, params

    def get(self):
        """ 任务管理-页任务管理"""
        try:
            kwargs = self.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            cd, params = self.get_task_search_condition(self.request.query, 'page')
            docs, pager, q, order = self.find_by_page(self, cd, self.search_fields, '-_id', {'params': 0, 'result': 0})
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
                {'$sort': {'count': -1}},
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
            submitted = self.prop(self.task, 'steps.submitted', [])
            steps_finished = self.prop(self.task, 'result.steps_finished') or 'box' in submitted
            steps_unfinished = True if steps_finished is None else not steps_finished
            self.render('page_box.html', page=page, img_url=img_url, steps_unfinished=steps_unfinished,
                        readonly=self.readonly)


class PageTaskTextHandler(PageHandler):
    URL = ['/task/(text_proof|text_review)/@task_id',
           '/task/do/(text_proof|text_review)/@task_id',
           '/task/browse/(text_proof|text_review)/@task_id',
           '/task/update/(text_proof|text_review)/@task_id']

    def get(self, task_type, task_id):
        """ 文字校对、审定页面"""
        try:
            self.page_title = '文字审定' if task_type == 'text_review' else '文字校对'
            PageTxtHandler.page_txt(self, self.task['doc_id'])

        except Exception as error:
            return self.send_db_error(error)
