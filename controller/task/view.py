#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from bson import json_util
from bson.objectid import ObjectId
from controller import errors as e
from controller.task.base import TaskHandler


class PageTaskLobbyHandler(TaskHandler):
    URL = '/task/lobby/@page_task'

    def get(self, task_type):
        """ 任务大厅"""
        try:
            q = self.get_query_argument('q', '')
            batch = self.prop(self.current_user, 'task_batch.%s' % task_type)
            tasks, total_count = self.find_lobby(task_type, q=q, batch=batch)
            fields = [('doc_id', '页编码'), ('char_count', '单字数量')]
            self.render('task_lobby.html', tasks=tasks, task_type=task_type, total_count=total_count,
                        fields=fields, batch=batch, format_value=self.format_value)
        except Exception as error:
            return self.send_db_error(error)


class CharTaskLobbyHandler(TaskHandler):
    URL = '/task/lobby/@char_task'

    def format_value(self, value, key=None, doc=None):
        if key == 'txt_kind' and len(value) > 5:
            return value[:5] + '...'
        return super().format_value(value, key, doc)

    def get(self, task_type):
        """ 任务大厅"""
        try:
            q = self.get_query_argument('q', '')
            batch = self.prop(self.current_user, 'task_batch.%s' % task_type)
            tasks, total_count = self.find_lobby(task_type, q=q, batch=batch)
            fields = [('txt_kind', '字种'), ('char_count', '单字数量')]
            self.render('task_lobby.html', tasks=tasks, task_type=task_type, total_count=total_count,
                        fields=fields, batch=batch, format_value=self.format_value)
        except Exception as error:
            return self.send_db_error(error)


class MyPageTaskHandler(TaskHandler):
    URL = '/task/my/@page_task'

    table_fields = [
        {'id': 'batch', 'name': '批次'},
        {'id': 'doc_id', 'name': '页编码'},
        {'id': 'num', 'name': '校次'},
        {'id': 'status', 'name': '状态'},
        {'id': 'char_count', 'name': '单字数量'},
        {'id': 'added', 'name': '新增'},
        {'id': 'deleted', 'name': '删除'},
        {'id': 'changed', 'name': '修改'},
        {'id': 'total', 'name': '所有'},
        {'id': 'used_time', 'name': '执行时间(秒)'},
        {'id': 'picked_time', 'name': '领取时间'},
        {'id': 'finished_time', 'name': '完成时间'},
        {'id': 'my_remark', 'name': '我的备注'},
    ]
    search_fields = ['batch', 'doc_id', 'my_remark']
    search_tips = '请搜索批次、页编码和我的备注'
    operations = [
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
        {'operation': 'btn-browse', 'label': '浏览结果'},
        {'operation': 'btn-dashboard', 'label': '结果统计'},
    ]
    actions = [
        {'action': 'my-task-view', 'label': '查看'},
        {'action': 'my-task-update', 'label': '更新'},
        {'action': 'my-task-remark', 'label': '备注'},
    ]
    update_fields = []

    def get_points(self, task_type):
        counts = list(self.db.task.aggregate([
            {'$match': {'task_type': task_type, 'status': self.STATUS_FINISHED, 'picked_user_id': self.user_id}},
            {'$group': {'_id': None, 'count': {'$sum': '$char_count'}}},
        ]))
        points = counts and counts[0]['count']
        return points

    def format_value(self, value, key=None, doc=None):
        if key == 'used_time' and value:
            return value / 1000
        return super().format_value(value, key, doc)

    def get(self, task_type):
        """ 我的任务"""
        try:
            kwargs = self.get_template_kwargs()
            kwargs['page_title'] = '我的任务-' + self.get_task_name(task_type)
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            cond, params = self.get_task_search_condition(self.request.query, 'page')
            status = {'$in': [self.STATUS_PICKED, self.STATUS_FINISHED]}
            cond.update({'task_type': task_type, 'status': status, 'picked_user_id': self.user_id})
            docs, pager, q, order = self.find_by_page(self, cond, default_order='-picked_time')
            self.render('task_my.html', task_type=task_type, docs=docs, pager=pager, q=q, order=order,
                        params=params, format_value=self.format_value, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class MyCharTaskHandler(TaskHandler):
    URL = '/task/my/@char_task'

    table_fields = [
        {'id': 'batch', 'name': '批次号'},
        {'id': 'doc_id', 'name': '页编码'},
        {'id': 'num', 'name': '校次'},
        {'id': 'status', 'name': '状态'},
        {'id': 'char_count', 'name': '单字数量'},
        {'id': 'picked_time', 'name': '领取时间'},
        {'id': 'finished_time', 'name': '完成时间'},
        {'id': 'used_time', 'name': '执行时间'},
    ]
    search_fields = ['doc_id', 'batch', 'remark']
    operations = [
        {'operation': 'btn-dashboard', 'label': '综合统计'},
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
        {'operation': 'btn-dashboard', 'label': '浏览结果'},
    ]
    actions = [
        {'action': 'my-task-view', 'label': '查看'},
        {'action': 'my-task-do', 'label': '继续', 'disabled': lambda d: d['status'] == 'finished'},
        {'action': 'my-task-update', 'label': '更新', 'disabled': lambda d: d['status'] == 'picked'},
        {'action': 'my-task-remark', 'label': '备注'},
    ]
    update_fields = []
    img_operations = []
    info_fields = ['my_remark']

    def get_points(self, task_type):
        counts = list(self.db.task.aggregate([
            {'$match': {'task_type': task_type, 'status': self.STATUS_FINISHED, 'picked_user_id': self.user_id}},
            {'$group': {'_id': None, 'count': {'$sum': '$char_count'}}},
        ]))
        points = counts and counts[0]['count']
        return points

    def get(self, task_type):
        """ 我的任务"""
        try:
            kwargs = self.get_template_kwargs()
            status = {'$in': [self.STATUS_PICKED, self.STATUS_FINISHED]}
            condition = {'task_type': task_type, 'status': status, 'picked_user_id': self.user_id}
            docs, pager, q, order = self.find_by_page(self, condition, default_order='-picked_time')
            self.render('task_my.html', docs=docs, pager=pager, q=q, order=order,
                        point=self.get_points(task_type), format_value=self.format_value, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class TaskInfoHandler(TaskHandler):
    URL = '/task/info/@task_id'

    def get(self, task_id):
        """ 任务详情"""
        try:
            task = self.db.task.find_one({'_id': ObjectId(task_id)})
            if not task:
                self.send_error_response(e.no_object, message='没有找到该任务')
            self.render('task_info.html', task=task)

        except Exception as error:
            return self.send_db_error(error)


class TaskSampleHandler(TaskHandler):
    URL = '/task/sample/@task_type'

    def get(self, task_type):
        """ 练习任务"""
        try:
            aggregate = [{'$match': {'task_type': task_type, 'batch': '练习任务'}}, {'$sample': {'size': 1}}]
            tasks = list(self.db.task.aggregate(aggregate))
            if tasks:
                return self.redirect('/task/%s/%s' % (task_type, tasks[0]['_id']))
            else:
                return self.send_error_response(e.no_object, message='没有找到练习任务')

        except Exception as error:
            return self.send_db_error(error)
