#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务管理
@time: 2018/12/26
"""
import random
from datetime import datetime
from controller import errors
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
            pager = dict(cur_page=cur_page, item_count=total_count, page_size=page_size)
            self.render(
                'task_admin.html', task_type=task_type, tasks=tasks, pager=pager, order=order, task_conf=task_conf,
                task_meta=self.all_task_types(), is_mod_enabled=self.is_mod_enabled,
            )
        except Exception as e:
            return self.send_db_error(e, render=True)


class TaskLobbyHandler(TaskHandler):
    URL = '/task/lobby/@task_type'

    @staticmethod
    def get_lobby_tasks_by_type(self, task_type, page_size=None):
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
        page_size = page_size or self.config['pager']['page_size']
        if task_meta.get('groups'):
            condition = {'task_type': {'$regex': '.*%s.*' % task_type}, 'status': self.STATUS_OPENED}
            total_count = self.db.task.count_documents(condition)
            skip_no = get_skip_no()
            tasks = list(self.db.task.find(condition).skip(skip_no).sort('priority', -1).limit(page_size * 3))
            tasks = de_duplicate()
        else:
            condition = {'task_type': task_type, 'status': self.STATUS_OPENED}
            total_count = self.db.task.count_documents(condition)
            skip_no = get_skip_no()
            tasks = list(self.db.task.find(condition).skip(skip_no).sort('priority', -1).limit(page_size))

        return tasks, total_count

    def get(self, task_type):
        """ 任务大厅 """
        try:
            tasks, total_count = self.get_lobby_tasks_by_type(self, task_type)
            self.render('task_lobby.html', tasks=tasks, task_type=task_type, total_count=total_count)
        except Exception as e:
            self.send_db_error(e, render=True)


class MyTaskHandler(TaskHandler):
    URL = '/task/my/@task_type'

    def get_my_tasks_by_type(self, task_type, q=None, order=None, page_size=0, page_no=1):
        """获取我的任务/任务列表"""
        if task_type not in self.all_task_types():
            return [], 0

        task_meta = self.all_task_types()[task_type]
        condition = {
            'task_type': {'$regex': '.*%s.*' % task_type} if task_meta.get('groups') else task_type,
            'picked_user_id': self.current_user['_id'],
            'status': {"$in": [self.STATUS_PICKED, self.STATUS_FINISHED]}
        }
        if q:
            condition.update({'doc_id': {'$regex': '.*%s.*' % q}})
        total_count = self.db.task.count_documents(condition)
        query = self.db.task.find(condition)
        if order:
            order, asc = (order[1:], -1) if order[0] == '-' else (order, 1)
            query.sort(order, asc)
        page_size = page_size or self.config['pager']['page_size']
        page_no = page_no if page_no >= 1 else 1
        tasks = query.skip(page_size * (page_no - 1)).limit(page_size)
        return list(tasks), total_count

    def get(self, task_type):
        """ 我的任务 """
        try:
            q = self.get_query_argument('q', '').upper()
            order = self.get_query_argument('order', '-picked_time')
            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            tasks, total_count = self.get_my_tasks_by_type(
                task_type=task_type, q=q, order=order, page_size=page_size, page_no=cur_page
            )
            pager = dict(cur_page=cur_page, item_count=total_count, page_size=page_size)
            self.render('my_task.html', task_type=task_type, tasks=tasks, pager=pager, order=order)
        except Exception as e:
            return self.send_db_error(e, render=True)


class PageTaskInfoHandler(TaskHandler):
    URL = '/task/page/@page_name'

    def get(self, page_name):
        """ 页面任务详情 """

        def format_info(key, value):
            """ 格式化任务信息"""
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M')
            elif key == 'task_type':
                value = self.get_task_name(value)
            elif key == 'status':
                value = self.get_status_name(value)
            elif key == 'pre_tasks':
                value = '/'.join([self.get_task_name(t) for t in value])
            elif key == 'steps':
                value = '/'.join([self.get_step_name(t) for t in value.get('todo', [])])
            elif key == 'priority':
                value = self.get_priority_name(int(value))
            return value

        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(errors.no_object, message='页面不存在')
            tasks = list(self.db.task.find({'collection': 'page', 'doc_id': page_name}))
            display_fields = ['doc_id', 'task_type', 'status', 'pre_tasks', 'steps', 'priority',
                              'updated_time', 'finished_time', 'publish_by', 'publish_time',
                              'picked_by', 'picked_time', 'returned_reason']

            self.render('task_info.html', page=page, tasks=tasks, format_info=format_info,
                        display_fields=display_fields)

        except Exception as e:
            return self.send_db_error(e, render=True)
