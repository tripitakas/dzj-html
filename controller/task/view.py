#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务管理
@time: 2018/12/26
"""
import re
import random
from datetime import datetime
from bson import json_util
from bson.objectid import ObjectId
from controller import errors as e
from controller.task.base import TaskHandler


class PageTask(TaskHandler):
    def get_search_condition(self):
        """ 获取查询条件"""
        condition, params = dict(collection='page'), dict()
        for field in ['batch', 'task_type', 'doc_id', 'status', 'priority', 'remark']:
            value = self.get_query_argument(field, '')
            if value:
                params[field] = value
                condition.update({field: {'$regex': value, '$options': '$i'}})
        picked_user_id = self.get_query_argument('picked_user_id', '')
        if picked_user_id:
            params['picked_user_id'] = picked_user_id
            condition.update({'picked_user_id': ObjectId(picked_user_id)})
        finished_start = self.get_query_argument('finished_start', '')
        if finished_start:
            params['finished_start'] = finished_start
            condition.update({'finished_time': {'$gt': datetime.strptime(finished_start, '%Y-%m-%d %H:%M:%S')}})
        finished_end = self.get_query_argument('finished_end', '')
        if finished_end:
            params['finished_end'] = finished_end
            condition.update({'finished_time': {'$lt': datetime.strptime(finished_end, '%Y-%m-%d %H:%M:%S')}})
        publish_start = self.get_query_argument('publish_start', '')
        if publish_start:
            params['publish_start'] = publish_start
            condition.update({'publish_time': {'$gt': datetime.strptime(publish_start, '%Y-%m-%d %H:%M:%S')}})
        publish_end = self.get_query_argument('publish_end', '')
        if publish_end:
            params['publish_end'] = publish_end
            condition.update({'publish_time': {'$lt': datetime.strptime(publish_end, '%Y-%m-%d %H:%M:%S')}})
        return condition, params

    def get_page_task(self, task_id):
        """ 根据task_id/to以及其它查询条件，获取页任务"""
        current_task = self.db.task.find_one({'_id': ObjectId(task_id)})
        if not current_task:
            self.send_error_response(e.no_object, message='没有找到任务%s' % task_id)
            return None
        to = self.get_query_argument('to', '')
        condition = self.get_search_condition()[0]
        if to == 'next':
            condition.update({'_id': {'$lt': ObjectId(task_id)}})
        elif to == 'prev':
            condition.update({'_id': {'$gt': ObjectId(task_id)}})
        else:
            condition.update({'_id': ObjectId(task_id)})
        to_task = self.db.task.find_one(condition, sort=[('_id', 1 if to == 'prev' else -1)])
        if not to_task:
            message = '没有找到任务%s的%s任务' % (task_id, '前一个' if to == 'prev' else '后一个')
            self.send_error_response(e.no_object, message=message)
            return False
        elif current_task['task_type'] != to_task['task_type']:
            query = re.sub('[?&]to=(prev|next)', '', self.request.query)
            url = '/task/admin/%s/%s?' % (to_task['task_type'], to_task['_id']) + query
            self.redirect(url.rstrip('?'))
            return False
        else:
            return to_task


class PageTaskAdminHandler(PageTask):
    URL = '/task/admin/page'

    page_title = '页任务管理'
    search_tips = '请搜索页编码、批次号或备注'
    search_fields = ['doc_id', 'batch', 'remark']
    operations = [
        {'operation': 'bat-remove', 'label': '批量删除', 'title': '/task/delete'},
        {'operation': 'bat-assign', 'label': '批量指派', 'data-target': 'assignModal'},
        {'operation': 'bat-update', 'label': '更新批次', 'data-target': 'updateModal'},
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
        {'operation': 'btn-statistic', 'label': '结果统计', 'groups': [
            {'operation': 'picked_user_id', 'label': '按用户'},
            {'operation': 'task_type', 'label': '按类型'},
            {'operation': 'status', 'label': '按状态'},
        ]},
        {'operation': 'btn-publish', 'label': '发布任务', 'groups': [
            {'operation': k, 'label': v} for k, v in TaskHandler.get_page_tasks().items()
        ]},
    ]
    actions = [
        {'action': 'btn-nav', 'label': '浏览'},
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-history', 'label': '历程'},
        {'action': 'btn-delete', 'label': '删除'},
        {'action': 'btn-republish', 'label': '重新发布'},
    ]
    table_fields = [
        {'id': '_id', 'name': '主键'},
        {'id': 'doc_id', 'name': '页编码'},
        {'id': 'batch', 'name': '批次号'},
        {'id': 'task_type', 'name': '类型', 'filter': TaskHandler.get_page_tasks()},
        {'id': 'status', 'name': '状态', 'filter': TaskHandler.task_statuses},
        {'id': 'priority', 'name': '优先级', 'filter': TaskHandler.priorities},
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
    hide_fields = ['_id', 'return_reason', 'create_time', 'updated_time', 'publish_by']
    modal_fields = [
        {'id': 'batch', 'name': '任务批次'},
    ]

    def get(self):
        """ 任务管理/页任务管理"""
        try:
            kwargs = self.get_page_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            condition, params = self.get_search_condition()
            docs, pager, q, order = self.find_by_page(self, condition, self.search_fields, '-_id')
            self.render(
                'task_admin_page.html', docs=docs, pager=pager, order=order, q=q, params=params,
                is_mod_enabled=self.is_mod_enabled, **kwargs,
            )
        except Exception as error:
            return self.send_db_error(error)


class TaskAdminImageHandler(TaskHandler):
    URL = '/task/admin/image'

    page_title = '页图片任务管理'
    search_tips = '请搜索批次、网盘名称或导入文件夹'
    search_fields = ['batch', 'input.pan_name', 'input.import_dir']
    operations = [
        {'operation': 'bat-remove', 'label': '批量删除', 'title': '/task/delete'},
        {'operation': 'btn-publish', 'label': '发布任务', 'data-target': 'publishModal'},
    ]
    actions = [
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-remove', 'label': '删除', 'title': '/task/delete'},
        {'action': 'btn-republish', 'label': '重新发布'},
    ]
    table_fields = [
        {'id': '_id', 'name': '主键'},
        {'id': 'batch', 'name': '批次'},
        {'id': 'input-pan_name', 'name': '网盘名称'},
        {'id': 'input-import_dir', 'name': '导入文件夹'},
        {'id': 'input-layout', 'name': '版面结构'},
        {'id': 'input-redo', 'name': '是否覆盖已有图片'},
        {'id': 'status', 'name': '状态'},
        {'id': 'priority', 'name': '优先级', 'filter': TaskHandler.priorities},
        {'id': 'return_reason', 'name': '退回理由'},
        {'id': 'create_time', 'name': '创建时间'},
        {'id': 'updated_time', 'name': '更新时间'},
        {'id': 'publish_time', 'name': '发布时间'},
        {'id': 'publish_by', 'name': '发布人'},
        {'id': 'picked_time', 'name': '领取时间'},
        {'id': 'picked_by', 'name': '领取人'},
        {'id': 'finished_time', 'name': '完成时间'},
    ]
    hide_fields = ['_id', 'return_reason', 'create_time', 'updated_time', 'publish_by']
    modal_fields = []

    def get(self):
        """ 任务管理/页图片任务 """
        try:
            kwargs = self.get_page_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            condition = dict(task_type='import_image')
            priority = self.get_query_argument('priority', '')
            if priority:
                condition.update({'priority': int(priority)})
            docs, pager, q, order = self.find_by_page(self, condition, default_order='-publish_time')
            self.render(
                'task_admin_import.html', docs=docs, pager=pager, order=order, q=q,
                pan_name=self.prop(self.config, 'pan.name'), **kwargs,
            )

        except Exception as error:
            return self.send_db_error(error)


class TaskLobbyHandler(TaskHandler):
    URL = '/task/lobby/@task_type'

    @staticmethod
    def get_lobby_tasks_by_type(self, task_type, page_size=None, q=None):
        """ 按优先级排序后随机获取任务大厅的任务列表"""

        def get_random_skip():
            condition.update({'priority': 3})
            n3 = self.db.task.count_documents(condition)
            condition.update({'priority': 2})
            n2 = self.db.task.count_documents(condition)
            condition.pop('priority', 0)
            skip = n3 if n3 > page_size else n3 + n2 if n3 + n2 > page_size else total_count
            return random.randint(1, skip - page_size) if skip > page_size else 0

        def de_duplicate():
            _tasks, _doc_ids = [], []
            for task in tasks:
                if task.get('doc_id') not in _doc_ids:
                    _tasks.append(task)
                    _doc_ids.append(task.get('doc_id'))
            return _tasks[:page_size]

        assert task_type in self.all_task_types()
        page_size = page_size or int(self.config['pager']['page_size'])
        condition = {'doc_id': {'$regex': q, '$options': '$i'}} if q else {}
        if self.is_group(task_type):
            condition.update({'task_type': {'$regex': task_type}, 'status': self.STATUS_PUBLISHED})
            my_tasks = self.find_many(task_type, mine=True)
            if my_tasks:
                condition.update({'doc_id': {'$nin': [t['doc_id'] for t in my_tasks]}})
            total_count = self.db.task.count_documents(condition)
            skip_no = get_random_skip()
            tasks = list(self.db.task.find(condition).skip(skip_no).sort('priority', -1).limit(page_size * 3))
            tasks = de_duplicate()
        else:
            condition.update({'task_type': task_type, 'status': self.STATUS_PUBLISHED})
            total_count = self.db.task.count_documents(condition)
            skip_no = get_random_skip()
            tasks = list(self.db.task.find(condition).skip(skip_no).sort('priority', -1).limit(page_size))

        return tasks, total_count

    def get(self, task_type):
        """ 任务大厅 """
        try:
            q = self.get_query_argument('q', '')
            tasks, total_count = self.get_lobby_tasks_by_type(self, task_type, q=q)
            self.render('task_lobby.html', tasks=tasks, task_type=task_type, total_count=total_count)
        except Exception as error:
            return self.send_db_error(error)


class MyTaskHandler(TaskHandler):
    URL = '/task/my/@task_type'

    search_tips = '请搜索页编码'
    search_fields = ['doc_id']
    operations = []
    actions = [
        {'action': 'my-task-view', 'label': '查看'},
        {'action': 'my-task-do', 'label': '继续'},
        {'action': 'my-task-update', 'label': '修改'},
    ]
    table_fields = [
        {'id': 'doc_id', 'name': '页编码'},
        {'id': 'task_type', 'name': '类型'},
        {'id': 'status', 'name': '状态'},
        {'id': 'picked_time', 'name': '领取时间'},
        {'id': 'finished_time', 'name': '完成时间'},
    ]
    hide_fields = ['task_type']
    modal_fields = []

    def get(self, task_type):
        """ 我的任务 """
        try:
            condition = {
                'task_type': {'$regex': task_type} if self.is_group(task_type) else task_type,
                'status': {'$in': [self.STATUS_PICKED, self.STATUS_FINISHED]},
                'picked_user_id': self.current_user['_id']
            }
            docs, pager, q, order = self.find_by_page(self, condition, default_order='-picked_time')
            kwargs = self.get_page_kwargs()
            self.render('my_task.html', docs=docs, pager=pager, q=q, order=order, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class PageTaskResumeHandler(TaskHandler):
    URL = '/task/resume/page/@page_name'

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
        """ 页面任务简历 """
        from functools import cmp_to_key
        try:
            page = self.db.page.find_one({'name': page_name}) or dict(name=page_name)
            tasks = list(self.db.task.find({'collection': 'page', 'doc_id': page_name}))
            tasks.sort(key=cmp_to_key(lambda a, b: self.order.index(a['task_type']) - self.order.index(b['task_type'])))
            self.render('task_resume.html', page=page, tasks=tasks, display_fields=self.display_fields)

        except Exception as error:
            return self.send_db_error(error)


class TaskDetailHandler(TaskHandler):
    URL = '/task/detail/@task_id'

    display_fields = [
        'doc_id', 'task_type', 'status', 'priority', 'pre_tasks', 'steps',
        'publish_time', 'publish_by', 'picked_time', 'picked_by',
        'updated_time', 'finished_time', 'message'
    ]

    def get(self, task_id):
        """ 页面任务详情 """
        try:
            task = self.db.task.find_one({'_id': ObjectId(task_id)})
            if not task:
                self.send_error_response(e.no_object, message='没有找到该任务')
            self.render('task_detail.html', task=task, display_fields=self.display_fields)

        except Exception as error:
            return self.send_db_error(error)
