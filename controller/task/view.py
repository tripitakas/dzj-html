#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bson.objectid import ObjectId
from controller import errors as e
from controller.task.base import TaskHandler


class TaskLobbyHandler(TaskHandler):
    URL = '/task/lobby/@task_type'

    def format_value(self, value, key=None, doc=None):
        """ 格式化task表的字段输出"""
        if key == 'txt_kind' and len(value) > 5:
            value = value[:5] + '...'
        return super().format_value(value, key, doc)

    def get(self, task_type):
        """ 任务大厅"""
        try:
            q = self.get_query_argument('q', '')
            tasks, total_count = self.find_lobby(task_type, q=q)
            collection = self.prop(self.task_types, task_type + '.data.collection')
            fields = [('txt_kind', '字种'), ('char_count', '单字数量')] if collection == 'char' else [
                ('doc_id', '页编码'), ('char_count', '单字数量')]
            self.render('task_lobby.html', tasks=tasks, task_type=task_type, total_count=total_count,
                        fields=fields, format_value=self.format_value)
        except Exception as error:
            return self.send_db_error(error)


class TaskMyHandler(TaskHandler):
    URL = '/task/my/@task_type'

    operations = []
    img_operations = []
    actions = [
        {'action': 'my-task-view', 'label': '查看'},
        {'action': 'my-task-do', 'label': '继续', 'disabled': lambda d: d['status'] == 'finished'},
        {'action': 'my-task-update', 'label': '更新', 'disabled': lambda d: d['status'] == 'picked'},
    ]
    hide_fields = ['task_type']
    info_fields = ['doc_id', 'task_type', 'status', 'picked_time', 'finished_time']
    update_fields = []

    @classmethod
    def set_template_kwargs(cls, collection):
        if collection == 'page':
            cls.search_tips = '请搜索页编码'
            cls.search_fields = ['doc_id']
            cls.table_fields = [{'id': 'doc_id', 'name': '页编码'}]
        else:
            cls.search_tips = '请搜索字种'
            cls.search_fields = ['txt_kind']
            cls.table_fields = [{'id': 'txt_kind', 'name': '字种'}]
        cls.table_fields.extend([
            {'id': 'char_count', 'name': '单字数量'},
            {'id': 'task_type', 'name': '类型'},
            {'id': 'status', 'name': '状态'},
            {'id': 'picked_time', 'name': '领取时间'},
            {'id': 'finished_time', 'name': '完成时间'},
        ])

    def format_value(self, value, key=None, doc=None):
        """ 格式化task表的字段输出"""
        if key == 'txt_kind' and len(value) > 5:
            return value[:5] + '...'
        return super().format_value(value, key, doc)

    def get(self, task_type):
        """ 我的任务"""
        try:
            collection = self.prop(self.task_types, task_type + '.data.collection')
            self.set_template_kwargs(collection)
            kwargs = self.get_template_kwargs()
            status = {'$in': [self.STATUS_PICKED, self.STATUS_FINISHED]}
            condition = {'task_type': task_type, 'status': status, 'picked_user_id': self.user_id}
            docs, pager, q, order = self.find_by_page(self, condition, default_order='-picked_time')
            condition['status'] = self.STATUS_FINISHED
            counts = list(self.db.task.aggregate([
                {'$match': condition}, {'$group': {'_id': None, 'count': {'$sum': '$char_count'}}},
            ]))
            point = counts and counts[0]['count']
            self.render('task_my.html', docs=docs, pager=pager, q=q, order=order, point=point,
                        format_value=self.format_value, **kwargs)

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
