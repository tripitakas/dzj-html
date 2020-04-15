#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务管理
@time: 2018/12/26
"""
import re
from bson import json_util
from bson.objectid import ObjectId
from controller import errors as e
from controller.task.base import TaskHandler


class CharTaskAdminHandler(TaskHandler):
    URL = '/task/admin/char'

    page_title = '字任务管理'
    search_tips = '请搜索字种、批次号或备注'
    search_fields = ['params.ocr_txt', 'params.txt', 'batch', 'remark']
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
        {'action': 'btn-delete', 'label': '删除'},
        {'action': 'btn-republish', 'label': '重新发布', 'disabled': lambda d: d['status'] not in ['picked', 'failed']},
    ]
    hide_fields = ['_id', 'params', 'return_reason', 'create_time', 'updated_time', 'publish_by']
    update_fields = []

    def get(self):
        """ 任务管理-字任务管理"""
        try:
            # 模板参数
            kwargs = self.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            kwargs['table_fields'] = [
                {'id': '_id', 'name': '主键'},
                {'id': 'batch', 'name': '批次号'},
                {'id': 'txt_kind', 'name': '字种'},
                {'id': 'char_count', 'name': '单字数量'},
                {'id': 'task_type', 'name': '类型', 'filter': self.get_task_types('char')},
                {'id': 'type_tips', 'name': '类型说明'},
                {'id': 'status', 'name': '状态', 'filter': self.task_statuses},
                {'id': 'priority', 'name': '优先级', 'filter': self.priorities},
                {'id': 'params', 'name': '输入参数'},
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
            condition, params = self.get_task_search_condition(self.request.query, 'char')
            docs, pager, q, order = self.find_by_page(self, condition, self.search_fields, '-_id')
            self.render(
                'task_admin_char.html', docs=docs, pager=pager, order=order, q=q, params=params,
                format_value=self.format_value, **kwargs,
            )
        except Exception as error:
            return self.send_db_error(error)


class PageTaskStatisticHandler(TaskHandler):
    URL = '/task/char/statistic'

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


class LobbyTaskHandler(TaskHandler):
    URL = '/task/lobby/@task_type'

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


class MyTaskHandler(TaskHandler):
    URL = '/task/my/@task_type'

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
