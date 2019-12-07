#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务管理
@time: 2018/12/26
"""
import random
from controller import errors
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from controller.helper import get_date_time
from controller.task.base import TaskHandler


class TaskAdminHandler(TaskHandler):
    URL = '/task/admin/@task_type'

    def is_mod_enabled(self, mod):
        disabled_mods = self.prop(self.config, 'modules.disabled_mods')
        return not disabled_mods or mod not in disabled_mods

    def get_tasks_by_type(self, task_type, status=None, q=None, order=None, page_size=0, page_no=1):
        """获取任务管理/任务列表"""

        group_task = self.all_task_types()[task_type].get('groups')
        condition = {'task_type': {'$regex': '.*%s.*' % task_type} if group_task else task_type}
        if status:
            condition.update({'status': status})
        if q:
            condition.update({'doc_id': {'$regex': '.*%s.*' % q}})
        total_count = self.db.task.count_documents(condition)
        query = self.db.task.find(condition)
        if order:
            order, asc = (order[1:], -1) if order[0] == '-' else (order, 1)
            query.sort(order, asc)
        page_size = page_size or self.config['pager']['page_size']
        page_no = page_no if page_no >= 1 else 1
        pages = query.skip(page_size * (page_no - 1)).limit(page_size)
        return list(pages), total_count

    def get(self, task_type):
        """ 任务管理/任务列表 """

        try:
            q = self.get_query_argument('q', '').upper()
            status = self.get_query_argument('status', '')
            order = self.get_query_argument('order', '')
            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            tasks, total_count = self.get_tasks_by_type(
                task_type, status=status, q=q, order=order, page_size=page_size, page_no=cur_page
            )
            task_conf = self.all_task_types()[task_type]
            pan_name = self.prop(self.config, 'pan.name')
            pager = dict(cur_page=cur_page, item_count=total_count, page_size=page_size)
            template = 'task_admin_import.html' if task_type == 'import_image' else 'task_admin.html'
            self.render(
                template, task_type=task_type, tasks=tasks, pager=pager, order=order, task_conf=task_conf,
                task_meta=self.all_task_types(), is_mod_enabled=self.is_mod_enabled, pan_name=pan_name,
            )
        except Exception as e:
            return self.send_db_error(e, render=True)


class TaskLobbyHandler(TaskHandler):
    URL = '/task/lobby/@task_type'

    @staticmethod
    def get_lobby_tasks_by_type(self, task_type, page_size=None, q=None):
        """按优先级排序后随机获取任务大厅/任务列表"""

        def get_skip_no():
            condition.update({'priority': 3})
            n3 = self.db.task.count_documents(condition)
            condition.update({'priority': 2})
            n2 = self.db.task.count_documents(condition)
            del condition['priority']
            skip = n3 if n3 > page_size else n3 + n2 if n3 + n2 > page_size else total_count
            return random.randint(1, skip - page_size) if skip > page_size else 0

        def de_duplicate():
            """根据doc_id去重"""
            _tasks, _doc_ids = [], []
            for task in tasks:
                if task.get('doc_id') not in _doc_ids:
                    _tasks.append(task)
                    _doc_ids.append(task.get('doc_id'))
            return _tasks[:page_size]

        if task_type not in self.all_task_types():
            return [], 0

        task_meta = self.all_task_types().get(task_type)
        page_size = page_size or int(self.config['pager']['page_size'])
        condition = {}
        if q:
            condition.update({'doc_id': {'$regex': '.*%s.*' % q}})
        if task_meta.get('groups'):
            condition.update({'task_type': {'$regex': '.*%s.*' % task_type}, 'status': self.STATUS_OPENED})
            my_tasks, count = MyTaskHandler.get_my_tasks_by_type(self, task_type, un_limit=True)
            if count:
                condition.update({'doc_id': {'$nin': [t['doc_id'] for t in my_tasks]}})
            total_count = self.db.task.count_documents(condition)
            skip_no = get_skip_no()
            tasks = list(self.db.task.find(condition).skip(skip_no).sort('priority', -1).limit(page_size * 3))
            tasks = de_duplicate()
        else:
            condition.update({'task_type': task_type, 'status': self.STATUS_OPENED})
            total_count = self.db.task.count_documents(condition)
            skip_no = get_skip_no()
            tasks = list(self.db.task.find(condition).skip(skip_no).sort('priority', -1).limit(page_size))

        return tasks, total_count

    def get(self, task_type):
        """ 任务大厅 """
        try:
            q = self.get_query_argument('q', '').upper()
            tasks, total_count = self.get_lobby_tasks_by_type(self, task_type, q=q)
            self.render('task_lobby.html', tasks=tasks, task_type=task_type, total_count=total_count)
        except Exception as e:
            self.send_db_error(e, render=True)


class MyTaskHandler(TaskHandler):
    URL = '/task/my/@task_type'

    @staticmethod
    def get_my_tasks_by_type(self, task_type=None, q=None, order=None, page_size=0, page_no=1, un_limit=None):
        """获取我的任务/任务列表"""
        if task_type and task_type not in self.all_task_types():
            return [], 0

        condition = {'status': {"$in": [self.STATUS_PICKED, self.STATUS_FINISHED]},
                     'picked_user_id': self.current_user['_id']}
        if task_type:
            task_meta = self.all_task_types()[task_type]
            condition.update({'task_type': {'$regex': '.*%s.*' % task_type} if task_meta.get('groups') else task_type})
        if q:
            condition.update({'doc_id': {'$regex': '.*%s.*' % q}})
        total_count = self.db.task.count_documents(condition)
        query = self.db.task.find(condition)
        if order:
            order, asc = (order[1:], -1) if order[0] == '-' else (order, 1)
            query.sort(order, asc)
        if not un_limit:
            page_size = page_size or self.config['pager']['page_size']
            page_no = page_no if page_no >= 1 else 1
            query.skip(page_size * (page_no - 1)).limit(page_size)
        return list(query), total_count

    def get(self, task_type):
        """ 我的任务 """
        try:
            q = self.get_query_argument('q', '').upper()
            order = self.get_query_argument('order', '-picked_time')
            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            tasks, total_count = self.get_my_tasks_by_type(
                self, task_type=task_type, q=q, order=order, page_size=page_size, page_no=cur_page
            )

            withdraw_time = get_date_time('%Y-%m-%d 02:00:00')  # 凌晨2点回收
            timeout_days = self.prop(self.application.load_config(), 'task.task_timeout_days')
            timeout = datetime.strptime(withdraw_time, '%Y-%m-%d %H:%M:%S') - timedelta(days=int(timeout_days))

            pager = dict(cur_page=cur_page, item_count=total_count, page_size=page_size)
            self.render('my_task.html', task_type=task_type, tasks=tasks, pager=pager, order=order, timeout=timeout)

        except Exception as e:
            return self.send_db_error(e, render=True)


class TaskPageInfoHandler(TaskHandler):
    URL = '/task/page/@page_name'

    @classmethod
    def format_info(cls, key, value):
        """ 格式化任务信息"""
        if isinstance(value, datetime):
            value = get_date_time('%Y-%m-%d %H:%M', value)
        elif key == 'task_type':
            value = cls.get_task_name(value)
        elif key == 'status':
            value = cls.get_status_name(value)
        elif key == 'pre_tasks':
            value = '/'.join([cls.get_task_name(t) for t in value])
        elif key == 'steps':
            value = '/'.join([cls.get_step_name(t) for t in value.get('todo', [])])
        elif key == 'priority':
            value = cls.get_priority_name(int(value))
        elif isinstance(value, dict):
            value = value.get('error') or value.get('message') \
                    or '<br/>'.join(['%s: %s' % (k, v) for k, v in value.items()])

        return value

    def get(self, page_name):
        """ Page的任务详情 """
        from functools import cmp_to_key

        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(errors.no_object, message='页面%s不存在' % page_name, render=True)

            tasks = list(self.db.task.find({'collection': 'page', 'doc_id': page_name}))
            order = ['upload_cloud', 'ocr_box', 'cut_proof', 'cut_review', 'ocr_text', 'text_proof_1',
                     'text_proof_2', 'text_proof_3', 'text_review', 'text_hard']
            tasks.sort(key=cmp_to_key(lambda a, b: order.index(a['task_type']) - order.index(b['task_type'])))
            display_fields = ['doc_id', 'task_type', 'status', 'pre_tasks', 'steps', 'priority',
                              'updated_time', 'finished_time', 'publish_by', 'publish_time',
                              'picked_by', 'picked_time', 'message']

            self.render('task_page_info.html', page=page, tasks=tasks, format_info=self.format_info,
                        display_fields=display_fields)

        except Exception as e:
            return self.send_db_error(e, render=True)


class TaskInfoHandler(TaskHandler):
    URL = '/task/info/@task_id'

    def get(self, task_id):
        """ 任务详情 """
        try:
            # 检查参数
            task = self.db.task.find_one({'_id': ObjectId(task_id)})
            if not task:
                self.send_error_response(errors.no_object, message='没有找到该任务')

            display_fields = ['doc_id', 'task_type', 'status', 'priority', 'pre_tasks', 'steps',
                              'publish_time', 'publish_by', 'picked_time', 'picked_by',
                              'updated_time', 'finished_time', 'message', ]

            self.render('task_info.html', task=task, display_fields=display_fields,
                        format_info=TaskPageInfoHandler.format_info)

        except Exception as e:
            return self.send_db_error(e, render=True)
