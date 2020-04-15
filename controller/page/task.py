#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from bson import json_util
from bson.objectid import ObjectId
from .base import PageHandler
from controller import errors as e
from .publish import PublishHandler


class PageTaskPublishApi(PublishHandler):
    URL = r'/api/page/task/publish'

    def post(self):
        """ 发布任务"""
        self.data['doc_ids'] = self.get_doc_ids(self.data)
        rules = [
            (v.not_empty, 'doc_ids', 'task_type', 'priority', 'force', 'batch'),
            (v.in_list, 'task_type', list(self.task_types.keys())),
            (v.in_list, 'pre_tasks', list(self.task_types.keys())),
            (v.is_priority, 'priority'),
        ]
        self.validate(self.data, rules)

        try:
            if len(self.data['doc_ids']) > self.MAX_PUBLISH_RECORDS:
                message = '任务数量不能超过%s' % self.MAX_PUBLISH_RECORDS
                return self.send_error_response(e.task_count_exceed, message=message)
            log = self.publish_many(
                self.data['task_type'], self.data.get('pre_tasks', []), self.data.get('steps', []),
                self.data['priority'], self.data['force'] == '是',
                self.data['doc_ids'], self.data['batch']
            )
            return self.send_data_response({k: value for k, value in log.items() if value})

        except self.DbError as error:
            return self.send_db_error(error)

    def get_doc_ids(self, data):
        """ 获取页码，有四种方式：页编码、文件、前缀、检索参数"""
        doc_ids = data.get('doc_ids') or []
        if doc_ids:
            return doc_ids
        ids_file = self.request.files.get('ids_file')
        collection, id_name, input_field = self.get_data_conf(data['task_type'])[:3]
        if ids_file:
            ids_str = str(ids_file[0]['body'], encoding='utf-8').strip('\n') if ids_file else ''
            try:
                doc_ids = json.loads(ids_str)
            except json.decoder.JSONDecodeError:
                ids_str = re.sub(r'\n+', '|', ids_str)
                doc_ids = ids_str.split(r'|')
        elif data.get('prefix'):
            condition = {id_name: {'$regex': data['prefix'], '$options': '$i'}}
            if input_field:
                condition[input_field] = {"$nin": [None, '']}
            doc_ids = [doc.get(id_name) for doc in self.db[collection].find(condition)]
        elif data.get('search'):
            condition = Page.get_page_search_condition(data['search'])[0]
            query = self.db[collection].find(condition)
            page = h.get_url_param('page', data['search'])
            if page:
                size = h.get_url_param('page_size', data['search']) or self.prop(self.config, 'pager.page_size', 10)
                query = query.skip((int(page) - 1) * int(size)).limit(int(size))
            doc_ids = [doc.get(id_name) for doc in list(query)]
        return doc_ids


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


class PageTaskStatisticHandler(PageHandler):
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


class PageLobbyTaskHandler(PageHandler):
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


class PageMyTaskHandler(PageHandler):
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
